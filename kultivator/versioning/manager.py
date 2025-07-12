"""
Git version management for Kultivator.

This module handles Git repository operations including initialization,
staging, committing, and maintaining a complete audit trail of AI changes.
"""

import logging
from pathlib import Path
from typing import List, Optional, Union, Any
from datetime import datetime

try:
    import git  # type: ignore
    from git import Repo, InvalidGitRepositoryError  # type: ignore
    GIT_AVAILABLE = True
except ImportError:
    git = None  # type: ignore
    Repo = None  # type: ignore
    InvalidGitRepositoryError = Exception  # type: ignore
    GIT_AVAILABLE = False


class VersionManager:
    """
    Manages Git operations for the Kultivator wiki repository.
    
    Provides functionality to initialize repositories, stage files, and create
    commits with descriptive messages tracking AI-generated changes.
    """
    
    def __init__(self, repo_path: str = "wiki"):
        """
        Initialize the version manager.
        
        Args:
            repo_path: Path to the Git repository (default: wiki directory)
        """
        self.repo_path = Path(repo_path)
        self.repo: Optional[Any] = None  # Using Any to avoid GitPython typing issues
        
        if not GIT_AVAILABLE:
            raise ImportError("GitPython package is required for versioning. Install with: pip install gitpython")
            
        logging.info(f"Initialized VersionManager for: {self.repo_path}")
    
    def initialize_repository(self) -> bool:
        """
        Initialize a Git repository if it doesn't exist.
        
        Returns:
            True if repository was initialized or already exists, False on error
        """
        try:
            # Check if repository already exists
            if self._is_git_repository():
                logging.info("Git repository already exists")
                self.repo = Repo(self.repo_path)  # type: ignore
                return True
            
            # Create the directory if it doesn't exist
            self.repo_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize new Git repository
            self.repo = Repo.init(self.repo_path)  # type: ignore
            
            # Create initial .gitignore
            gitignore_path = self.repo_path / ".gitignore"
            if not gitignore_path.exists():
                with open(gitignore_path, 'w') as f:
                    f.write("""# Kultivator Git ignore file
# Temporary files
*.tmp
*.temp
.DS_Store
Thumbs.db

# Editor files
.vscode/
.idea/
*.swp
*.swo
*~

# OS files
.DS_Store
Thumbs.db
""")
                
                # Add and commit .gitignore (use relative path)
                if self.repo is not None:
                    self.repo.index.add([".gitignore"])  # type: ignore
                    self.repo.index.commit("Initial commit: Add .gitignore")  # type: ignore
                
            logging.info("Git repository initialized successfully")
            return True
            
        except Exception as e:
            logging.error(f"Failed to initialize Git repository: {e}")
            return False
    
    def _is_git_repository(self) -> bool:
        """Check if the path is already a Git repository."""
        try:
            if not self.repo_path.exists():
                return False
            Repo(self.repo_path)  # type: ignore
            return True
        except InvalidGitRepositoryError:
            return False
    
    def stage_file(self, file_path: str) -> bool:
        """
        Stage a file for commit.
        
        Args:
            file_path: Path to the file to stage (relative to repo root)
            
        Returns:
            True if file was staged successfully, False otherwise
        """
        if not self.repo:
            logging.error("Repository not initialized")
            return False
            
        try:
            # Convert to relative path if absolute
            rel_path = Path(file_path)
            if rel_path.is_absolute():
                rel_path = rel_path.relative_to(self.repo_path)
            
            # Stage the file
            self.repo.index.add([str(rel_path)])  # type: ignore
            logging.info(f"Staged file: {rel_path}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to stage file {file_path}: {e}")
            return False
    
    def stage_files(self, file_paths: List[str]) -> bool:
        """
        Stage multiple files for commit.
        
        Args:
            file_paths: List of file paths to stage
            
        Returns:
            True if all files were staged successfully, False otherwise
        """
        if not self.repo:
            logging.error("Repository not initialized")
            return False
            
        try:
            # Convert to relative paths
            rel_paths = []
            for file_path in file_paths:
                rel_path = Path(file_path)
                if rel_path.is_absolute():
                    rel_path = rel_path.relative_to(self.repo_path)
                rel_paths.append(str(rel_path))
            
            # Stage all files
            self.repo.index.add(rel_paths)  # type: ignore
            logging.info(f"Staged {len(rel_paths)} files")
            return True
            
        except Exception as e:
            logging.error(f"Failed to stage files: {e}")
            return False
    
    def commit_changes(self, message: str, author_name: str = "Kultivator AI", 
                      author_email: str = "ai@kultivator.local") -> bool:
        """
        Commit staged changes with a descriptive message.
        
        Args:
            message: Commit message
            author_name: Name of the commit author
            author_email: Email of the commit author
            
        Returns:
            True if commit was successful, False otherwise
        """
        if not self.repo:
            logging.error("Repository not initialized")
            return False
            
        try:
            # Check if there are any staged changes
            if not self.repo.index.diff("HEAD"):  # type: ignore
                logging.info("No changes to commit")
                return True
            
            # Create commit with custom author
            commit = self.repo.index.commit(  # type: ignore
                message,
                author=git.Actor(author_name, author_email),  # type: ignore
                committer=git.Actor(author_name, author_email)  # type: ignore
            )
            
            logging.info(f"Created commit: {commit.hexsha[:8]} - {message}")  # type: ignore
            return True
            
        except Exception as e:
            logging.error(f"Failed to commit changes: {e}")
            return False
    
    def stage_and_commit(self, file_paths: List[str], message: str) -> bool:
        """
        Stage files and commit them in one operation.
        
        Args:
            file_paths: List of file paths to stage and commit
            message: Commit message
            
        Returns:
            True if operation was successful, False otherwise
        """
        if self.stage_files(file_paths):
            return self.commit_changes(message)
        return False
    
    def create_bootstrap_commit(self, entity_count: int, block_count: int) -> bool:
        """
        Create the initial bootstrap commit after processing all data.
        
        Args:
            entity_count: Number of entities processed
            block_count: Number of blocks processed
            
        Returns:
            True if commit was successful, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""Bootstrap: Initial knowledge base generation

Generated by Kultivator AI on {timestamp}

Statistics:
- {entity_count} entities discovered and processed
- {block_count} source blocks analyzed
- Wiki pages created with AI-generated content

This commit represents the initial state of the knowledge base
generated from the source data. All subsequent commits will
track incremental updates and changes."""

        # Stage all files in the wiki directory
        try:
            # Get all files in the repository
            all_files = []
            for file_path in self.repo_path.rglob("*"):
                if file_path.is_file() and not file_path.name.startswith('.git'):
                    rel_path = file_path.relative_to(self.repo_path)
                    all_files.append(str(rel_path))
            
            return self.stage_and_commit(all_files, message)
            
        except Exception as e:
            logging.error(f"Failed to create bootstrap commit: {e}")
            return False
    
    def create_incremental_commit(self, entity_name: str, block_id: str, 
                                action: str = "update") -> bool:
        """
        Create an incremental commit for a single entity update.
        
        Args:
            entity_name: Name of the entity that was updated
            block_id: ID of the block that triggered the update
            action: Type of action (update, create, modify)
            
        Returns:
            True if commit was successful, False otherwise
        """
        if not self.repo:
            logging.error("Repository not initialized")
            return False
            
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        message = f"""AI: {action.title()} {entity_name}

Updated by Kultivator AI on {timestamp}
Source block: {block_id}

This commit represents an incremental update to the knowledge base
based on changes detected in the source data."""

        # Stage all modified files (Git will determine what changed)
        try:
            # Get all modified files
            modified_files = []
            
            # Check for unstaged changes
            for item in self.repo.index.diff(None):  # type: ignore
                modified_files.append(item.a_path)  # type: ignore
            
            # Check for untracked files
            for untracked in self.repo.untracked_files:  # type: ignore
                modified_files.append(untracked)
            
            if modified_files:
                return self.stage_and_commit(modified_files, message)
            else:
                logging.info("No changes detected for incremental commit")
                return True
                
        except Exception as e:
            logging.error(f"Failed to create incremental commit: {e}")
            return False
    
    def get_commit_history(self, limit: int = 10) -> List[dict]:
        """
        Get the commit history for the repository.
        
        Args:
            limit: Maximum number of commits to return
            
        Returns:
            List of commit information dictionaries
        """
        if not self.repo:
            logging.error("Repository not initialized")
            return []
            
        try:
            commits = []
            for commit in self.repo.iter_commits(max_count=limit):  # type: ignore
                commits.append({
                    'hash': commit.hexsha,  # type: ignore
                    'short_hash': commit.hexsha[:8],  # type: ignore
                    'message': commit.message.strip(),  # type: ignore
                    'author': str(commit.author),  # type: ignore
                    'date': commit.committed_datetime.isoformat(),  # type: ignore
                    'files_changed': len(commit.stats.files)  # type: ignore
                })
            
            return commits
            
        except Exception as e:
            logging.error(f"Failed to get commit history: {e}")
            return []
    
    def get_repository_status(self) -> dict:
        """
        Get the current repository status.
        
        Returns:
            Dictionary with repository status information
        """
        if not self.repo:
            return {"error": "Repository not initialized"}
            
        try:
            status = {
                'is_dirty': self.repo.is_dirty(),  # type: ignore
                'untracked_files': len(self.repo.untracked_files),  # type: ignore
                'modified_files': len(self.repo.index.diff(None)),  # type: ignore
                'staged_files': len(self.repo.index.diff("HEAD")),  # type: ignore
                'total_commits': len(list(self.repo.iter_commits())),  # type: ignore
                'active_branch': self.repo.active_branch.name if self.repo.active_branch else None  # type: ignore
            }
            
            return status
            
        except Exception as e:
            logging.error(f"Failed to get repository status: {e}")
            return {"error": str(e)} 