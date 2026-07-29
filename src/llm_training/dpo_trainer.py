"""
DPO Trainer Module
Implements Direct Preference Optimization for the SelfSmart LLM.
"""

import os
import hashlib
import json
from datetime import datetime
import torch
import logging
from typing import Dict, Any, Optional, List
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import DPOTrainer, DPOConfig
from datasets import Dataset

logger = logging.getLogger(__name__)


class DPOTrainerManager:
    """Manages the Direct Preference Optimization fine-tuning pipeline."""

    def __init__(
        self,
        model_name: str,
        output_dir: str = "./dpo_checkpoints",
        use_4bit: bool = False,
    ):
        self.model_name = model_name
        self.output_dir = output_dir
        self.use_4bit = use_4bit

        self.tokenizer = None
        self.model = None
        self.ref_model = None

        # Apple Silicon setup
        self.device = (
            "mps"
            if torch.backends.mps.is_available()
            else ("cuda" if torch.cuda.is_available() else "cpu")
        )

        # Handle macOS memory constraints by defaulting to fp16
        self.torch_dtype = torch.float16 if self.device != "cpu" else torch.float32

    def load_models(self):
        """Load the model and reference model."""
        logger.info(f"Loading Tokenizer from {self.model_name}")
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        kwargs = {
            "device_map": "auto" if self.device == "cuda" else self.device,
            "torch_dtype": self.torch_dtype,
            "trust_remote_code": True,
        }

        if self.use_4bit and self.device == "cuda":
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.float16,
            )

        logger.info(f"Loading Base Model from {self.model_name}")
        self.model = AutoModelForCausalLM.from_pretrained(self.model_name, **kwargs)

        # In DPO, we technically need a reference model.
        # If None is passed, DPOTrainer automatically creates a copy or handles it if we use PEFT.
        # Since we use PEFT (LoRA), the DPOTrainer can automatically use the base adapters as reference,
        # so we don't strictly need to load a second copy into VRAM!
        logger.info("Models loaded successfully.")

    def prepare_peft(self):
        """Prepare model for LoRA training."""
        if self.use_4bit and self.device == "cuda":
            self.model = prepare_model_for_kbit_training(self.model)

        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
            bias="none",
            task_type="CAUSAL_LM",
        )
        self.model = get_peft_model(self.model, lora_config)
        self.model.print_trainable_parameters()

    def format_dpo_dataset(self, data: List[Dict]) -> Dataset:
        """Format the dataset for DPOTrainer."""
        # DPOTrainer expects exactly: 'prompt', 'chosen', 'rejected' columns
        prompts = []
        chosen = []
        rejected = []

        for item in data:
            # We format prompt to match the chat template
            p = f"### Instruction:\\n{item['prompt']}\\n\\n### Assistant:\\n"
            prompts.append(p)
            chosen.append(item["chosen"])
            rejected.append(item["rejected"])

        dataset = Dataset.from_dict({"prompt": prompts, "chosen": chosen, "rejected": rejected})
        return dataset

    def train(self, dpo_pairs: List[Dict], data_hash: Optional[str] = None):
        """Execute the DPO training loop."""
        if not self.model:
            self.load_models()
            self.prepare_peft()

        dataset = self.format_dpo_dataset(dpo_pairs)

        # Compute data hash if not provided
        if data_hash is None:
            data_str = json.dumps(dpo_pairs, sort_keys=True)
            data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]

        logger.info(
            f"Starting DPO Training on {len(dataset)} preference pairs with data hash: {data_hash}..."
        )

        # Create versioned output directory
        timestamp = datetime.utcnow().isoformat()
        version_id = f"v{timestamp.replace(':', '-').replace('.', '-')}"
        version_output_dir = os.path.join(self.output_dir, version_id)
        os.makedirs(version_output_dir, exist_ok=True)

        # Optimize for Mac MPS
        optim = "adamw_torch" if self.device == "mps" else "paged_adamw_32bit"

        dpo_config = DPOConfig(
            output_dir=version_output_dir,
            beta=0.1,  # KL penalty parameter
            learning_rate=5e-5,
            per_device_train_batch_size=1,  # Very small batch for local DPO
            gradient_accumulation_steps=4,
            num_train_epochs=3,
            max_length=512,
            max_prompt_length=256,
            optim=optim,
            logging_steps=1,
            save_strategy="epoch",
            report_to="none",
        )

        trainer = DPOTrainer(
            model=self.model,
            ref_model=None,  # PEFT handles reference natively
            args=dpo_config,
            train_dataset=dataset,
            tokenizer=self.tokenizer,
        )

        trainer.train()

        logger.info("DPO Training complete. Saving adapters...")
        trainer.save_model(version_output_dir)
        self.tokenizer.save_pretrained(version_output_dir)

        # Save metadata
        metadata = {
            "timestamp": timestamp,
            "data_hash": data_hash,
            "num_pairs": len(dpo_pairs),
            "model_name": self.model_name,
            "use_4bit": self.use_4bit,
        }
        metadata_path = os.path.join(version_output_dir, "metadata.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=2)

        # Create symlink to latest version
        latest_link = os.path.join(self.output_dir, "latest")
        if os.path.exists(latest_link):
            os.remove(latest_link)
        try:
            os.symlink(version_output_dir, latest_link)
        except OSError:
            # Symlink may not work on all systems, skip
            pass

        logger.info(f"DPO model saved to {version_output_dir}")
        logger.info(f"Version ID: {version_id}")
        logger.info(f"Metadata saved to {metadata_path}")
