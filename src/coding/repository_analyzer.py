"""Repository analysis for code understanding and structure discovery."""

import os
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Set
from dataclasses import dataclass, asdict
import subprocess


@dataclass
class RepositoryMetadata:
    """Metadata about a code repository."""
    framework: Optional[str] = None
    language: str = "Unknown"
    tests: int = 0
    modules: int = 0
    total_loc: int = 0
    dependencies: List[str] = None
    architecture: Dict = None
    test_files: List[str] = None
    build_files: List[str] = None
    project_structure: Dict = None

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.architecture is None:
            self.architecture = {}
        if self.test_files is None:
            self.test_files = []
        if self.build_files is None:
            self.build_files = []
        if self.project_structure is None:
            self.project_structure = {}

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class RepositoryAnalyzer:
    """Analyzes code repositories to extract structure, dependencies, and metadata."""

    LANGUAGE_DETECTORS = {
        'py': 'Python',
        'js': 'JavaScript',
        'ts': 'TypeScript',
        'go': 'Go',
        'rs': 'Rust',
        'java': 'Java',
        'cpp': 'C++',
        'c': 'C',
        'rb': 'Ruby',
        'php': 'PHP',
    }

    FRAMEWORK_DETECTORS = {
        'Python': {
            'fastapi': ['fastapi', 'uvicorn'],
            'flask': ['flask'],
            'django': ['django'],
            'pytest': ['pytest'],
        },
        'JavaScript': {
            'express': ['express'],
            'react': ['react', 'react-dom'],
            'vue': ['vue'],
            'angular': ['@angular/core'],
        },
        'TypeScript': {
            'express': ['express', '@types/express'],
            'react': ['react', '@types/react'],
            'nest': ['@nestjs/common'],
        },
    }

    BUILD_FILES = {
        'Python': ['pyproject.toml', 'setup.py', 'requirements.txt', 'Pipfile'],
        'JavaScript': ['package.json', 'yarn.lock', 'package-lock.json'],
        'TypeScript': ['package.json', 'tsconfig.json'],
        'Go': ['go.mod', 'go.sum'],
        'Rust': ['Cargo.toml', 'Cargo.lock'],
        'Java': ['pom.xml', 'build.gradle'],
    }

    TEST_PATTERNS = {
        'Python': ['test_*.py', '*_test.py', 'tests/'],
        'JavaScript': ['*.test.js', '*.spec.js', '__tests__/'],
        'TypeScript': ['*.test.ts', '*.spec.ts', '__tests__/'],
        'Go': ['*_test.go'],
        'Rust': ['tests/', '*_test.rs'],
    }

    def __init__(self, repository_path: str):
        self.repository_path = Path(repository_path)
        self.metadata = RepositoryMetadata()

    def analyze(self, path: Optional[str] = None) -> RepositoryMetadata:
        """Perform full repository analysis."""
        if path:
            self.repository_path = Path(path)

        if not self.repository_path.exists():
            raise ValueError(f"Repository path does not exist: {self.repository_path}")

        self._detect_language()
        self._detect_framework()
        self._analyze_structure()
        self._discover_dependencies()
        self._discover_tests()
        self._discover_build()
        self._count_loc()
        self._discover_architecture()

        return self.metadata

    def _detect_language(self) -> str:
        """Detect primary programming language from file extensions."""
        extension_counts: Dict[str, int] = {}

        for file_path in self.repository_path.rglob('*'):
            if file_path.is_file():
                ext = file_path.suffix.lstrip('.')
                if ext in self.LANGUAGE_DETECTORS:
                    extension_counts[ext] = extension_counts.get(ext, 0) + 1

        if extension_counts:
            primary_ext = max(extension_counts, key=extension_counts.get)
            self.metadata.language = self.LANGUAGE_DETECTORS[primary_ext]

        return self.metadata.language

    def _detect_framework(self) -> Optional[str]:
        """Detect web framework from dependencies."""
        language = self.metadata.language
        if language not in self.FRAMEWORK_DETECTORS:
            return None

        frameworks = self.FRAMEWORK_DETECTORS[language]
        detected = []

        for framework, deps in frameworks.items():
            for dep in deps:
                if self._has_dependency(dep):
                    detected.append(framework)
                    break

        self.metadata.framework = detected[0] if detected else None
        return self.metadata.framework

    def _has_dependency(self, dep_name: str) -> bool:
        """Check if repository has a specific dependency."""
        dep_files = self.BUILD_FILES.get(self.metadata.language, [])
        
        for dep_file in dep_files:
            file_path = self.repository_path / dep_file
            if file_path.exists():
                content = file_path.read_text()
                if dep_name.lower() in content.lower():
                    return True

        return False

    def _analyze_structure(self) -> Dict:
        """Analyze project directory structure."""
        structure = {}
        self.metadata.modules = 0

        for item in self.repository_path.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                structure[item.name] = self._count_files_recursive(item)
                if item.name != 'tests' and item.name != '__pycache__':
                    self.metadata.modules += 1

        self.metadata.project_structure = structure
        return structure

    def _count_files_recursive(self, path: Path) -> int:
        """Count files in a directory recursively."""
        count = 0
        for item in path.rglob('*'):
            if item.is_file():
                count += 1
        return count

    def _discover_dependencies(self) -> List[str]:
        """Extract dependencies from build files."""
        language = self.metadata.language
        dep_files = self.BUILD_FILES.get(language, [])
        dependencies = []

        for dep_file in dep_files:
            file_path = self.repository_path / dep_file
            if file_path.exists():
                deps = self._parse_dependencies(file_path, language)
                dependencies.extend(deps)

        self.metadata.dependencies = list(set(dependencies))
        return self.metadata.dependencies

    def _parse_dependencies(self, file_path: Path, language: str) -> List[str]:
        """Parse dependencies from build file."""
        dependencies = []
        content = file_path.read_text()

        if language == 'Python':
            if file_path.name == 'pyproject.toml':
                try:
                    import tomli
                    data = tomli.loads(content)
                    deps = data.get('project', {}).get('dependencies', [])
                    dependencies.extend([d.split('>=')[0].split('==')[0] for d in deps])
                except ImportError:
                    pass
            elif file_path.name == 'requirements.txt':
                dependencies.extend([
                    line.split('>=')[0].split('==')[0].strip()
                    for line in content.split('\n')
                    if line and not line.startswith('#')
                ])

        elif language in ['JavaScript', 'TypeScript']:
            if file_path.name == 'package.json':
                try:
                    data = json.loads(content)
                    deps = data.get('dependencies', {})
                    dev_deps = data.get('devDependencies', {})
                    dependencies.extend(list(deps.keys()) + list(dev_deps.keys()))
                except json.JSONDecodeError:
                    pass

        elif language == 'Go':
            if file_path.name == 'go.mod':
                for line in content.split('\n'):
                    if line.strip().startswith('require '):
                        deps = line.split()[1:]
                        dependencies.extend(deps)

        elif language == 'Rust':
            if file_path.name == 'Cargo.toml':
                for line in content.split('\n'):
                    if '=' in line and not line.strip().startswith('#'):
                        dep = line.split('=')[0].strip()
                        if dep and not dep.startswith('['):
                            dependencies.append(dep)

        return dependencies

    def _discover_tests(self) -> List[str]:
        """Discover test files and count tests."""
        language = self.metadata.language
        patterns = self.TEST_PATTERNS.get(language, [])
        test_files = []

        for pattern in patterns:
            if '*' in pattern:
                for file_path in self.repository_path.rglob(pattern):
                    if file_path.is_file():
                        test_files.append(str(file_path.relative_to(self.repository_path)))
            else:
                test_dir = self.repository_path / pattern
                if test_dir.exists() and test_dir.is_dir():
                    for file_path in test_dir.rglob('*'):
                        if file_path.is_file():
                            test_files.append(str(file_path.relative_to(self.repository_path)))

        self.metadata.test_files = test_files
        self.metadata.tests = len(test_files)
        return test_files

    def _discover_build(self) -> List[str]:
        """Discover build configuration files."""
        language = self.metadata.language
        build_files = self.BUILD_FILES.get(language, [])
        found = []

        for build_file in build_files:
            file_path = self.repository_path / build_file
            if file_path.exists():
                found.append(build_file)

        self.metadata.build_files = found
        return found

    def _count_loc(self) -> int:
        """Count total lines of code."""
        total_loc = 0
        language_ext = None

        for ext, lang in self.LANGUAGE_DETECTORS.items():
            if lang == self.metadata.language:
                language_ext = ext
                break

        if language_ext:
            for file_path in self.repository_path.rglob(f'*.{language_ext}'):
                if file_path.is_file():
                    try:
                        total_loc += len(file_path.read_text().split('\n'))
                    except UnicodeDecodeError:
                        pass

        self.metadata.total_loc = total_loc
        return total_loc

    def _discover_architecture(self) -> Dict:
        """Discover architectural patterns and structure."""
        architecture = {
            'layers': [],
            'patterns': [],
            'components': []
        }

        # Detect common architectural patterns
        if self.metadata.language == 'Python':
            self._detect_python_architecture(architecture)

        self.metadata.architecture = architecture
        return architecture

    def _detect_python_architecture(self, architecture: Dict):
        """Detect Python-specific architectural patterns."""
        src_dirs = ['src', 'app', 'lib', 'core']
        layers = []

        for src_dir in src_dirs:
            src_path = self.repository_path / src_dir
            if src_path.exists():
                layers.append(src_dir)
                for item in src_path.iterdir():
                    if item.is_dir():
                        architecture['components'].append(item.name)

        if 'api' in str(self.repository_path):
            architecture['patterns'].append('api')
        if 'models' in str(self.repository_path) or 'schemas' in str(self.repository_path):
            architecture['patterns'].append('mvc')
        if 'services' in str(self.repository_path):
            architecture['patterns'].append('service_layer')

        architecture['layers'] = layers
