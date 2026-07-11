"""
Classification metrics for binary and multi-class evaluation.
"""

from typing import List, Tuple, Optional
import numpy as np
from .metric_types import Metric, MetricType


class ClassificationMetrics:
    """Compute classification metrics from predictions and ground truth."""
    
    @staticmethod
    def compute_confusion_matrix(
        predictions: List[int],
        ground_truth: List[int],
        num_classes: Optional[int] = None,
    ) -> np.ndarray:
        """Compute confusion matrix."""
        if num_classes is None:
            num_classes = max(max(predictions), max(ground_truth)) + 1
        
        cm = np.zeros((num_classes, num_classes), dtype=int)
        
        for pred, true in zip(predictions, ground_truth):
            cm[true][pred] += 1
        
        return cm
    
    @staticmethod
    def compute_binary_metrics(
        predictions: List[int],
        ground_truth: List[int],
    ) -> dict:
        """Compute binary classification metrics."""
        tp = sum(1 for p, t in zip(predictions, ground_truth) if p == 1 and t == 1)
        tn = sum(1 for p, t in zip(predictions, ground_truth) if p == 0 and t == 0)
        fp = sum(1 for p, t in zip(predictions, ground_truth) if p == 1 and t == 0)
        fn = sum(1 for p, t in zip(predictions, ground_truth) if p == 0 and t == 1)
        
        accuracy = (tp + tn) / (tp + tn + fp + fn) if (tp + tn + fp + fn) > 0 else 0.0
        
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        
        return {
            "true_positives": tp,
            "true_negatives": tn,
            "false_positives": fp,
            "false_negatives": fn,
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    
    @staticmethod
    def compute_multiclass_metrics(
        predictions: List[int],
        ground_truth: List[int],
        num_classes: Optional[int] = None,
    ) -> dict:
        """Compute multi-class classification metrics."""
        cm = ClassificationMetrics.compute_confusion_matrix(
            predictions, ground_truth, num_classes
        )
        
        # Per-class metrics
        num_classes = cm.shape[0]
        precisions = []
        recalls = []
        f1s = []
        
        for i in range(num_classes):
            tp = cm[i][i]
            fp = cm[:, i].sum() - tp
            fn = cm[i, :].sum() - tp
            
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )
            
            precisions.append(precision)
            recalls.append(recall)
            f1s.append(f1)
        
        # Macro averages
        macro_precision = np.mean(precisions)
        macro_recall = np.mean(recalls)
        macro_f1 = np.mean(f1s)
        
        # Micro averages
        total_tp = cm.diagonal().sum()
        total_fp = cm.sum(axis=0).sum() - total_tp
        total_fn = cm.sum(axis=1).sum() - total_tp
        
        micro_precision = (
            total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
        )
        micro_recall = (
            total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
        )
        micro_f1 = (
            2 * (micro_precision * micro_recall) / (micro_precision + micro_recall)
            if (micro_precision + micro_recall) > 0
            else 0.0
        )
        
        # Overall accuracy
        accuracy = total_tp / cm.sum()
        
        return {
            "confusion_matrix": cm.tolist(),
            "accuracy": accuracy,
            "macro_precision": macro_precision,
            "macro_recall": macro_recall,
            "macro_f1": macro_f1,
            "micro_precision": micro_precision,
            "micro_recall": micro_recall,
            "micro_f1": micro_f1,
            "per_class_precision": precisions,
            "per_class_recall": recalls,
            "per_class_f1": f1s,
        }
    
    @staticmethod
    def compute_roc_auc(
        scores: List[float],
        ground_truth: List[int],
    ) -> float:
        """Compute ROC AUC score."""
        try:
            from sklearn.metrics import roc_auc_score
            return roc_auc_score(ground_truth, scores)
        except ImportError:
            # Fallback to simple implementation
            # Sort by score
            sorted_pairs = sorted(zip(scores, ground_truth), key=lambda x: x[0], reverse=True)
            
            # Compute AUC using trapezoidal rule
            n = len(sorted_pairs)
            auc = 0.0
            tp = 0
            fp = 0
            prev_tp = 0
            prev_fp = 0
            
            for score, label in sorted_pairs:
                if label == 1:
                    tp += 1
                else:
                    fp += 1
                
                auc += (tp + prev_tp) * (fp - prev_fp) / 2
                prev_tp = tp
                prev_fp = fp
            
            # Normalize
            total_pos = sum(ground_truth)
            total_neg = len(ground_truth) - total_pos
            
            if total_pos == 0 or total_neg == 0:
                return 0.0
            
            return auc / (total_pos * total_neg)
