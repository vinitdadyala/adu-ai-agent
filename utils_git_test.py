import unittest
from unittest.mock import patch, Mock
import os
import requests
import utils_git
from git import Repo, GitCommandError
import pytest

class TestUtilsGit(unittest.TestCase):
    def test_parse_github_url_valid_https(self):
        url = "https://github.com/testowner/testrepo"
        owner, repo = utils_git.parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_ssh(self):
        url = "git@github.com:testowner/testrepo.git" 
        owner, repo = utils_git.parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_short(self):
        url = "testowner/testrepo"
        owner, repo = utils_git.parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_invalid(self):
        invalid_urls = [
            "invalid_url",
            "https://gitlab.com/owner/repo",
            "owner",
            "owner/repo/extra"
        ]
        for url in invalid_urls:
            with self.assertRaises(ValueError):
                utils_git.parse_github_url(url)

    @patch("subprocess.run")
    def test_branch_exists(self, mock_run):
        mock_run.return_value = Mock(stdout="  origin/main\n  origin/dev")
        self.assertTrue(utils_git.branch_exists("main"))
        self.assertFalse(utils_git.branch_exists("feature-branch"))

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        with patch("utils_git.branch_exists", return_value=False):
            utils_git.create_branch("feature-branch")
            mock_run.assert_any_call(["git", "checkout", "-b", "feature-branch"], check=True)
            mock_run.assert_any_call(["git", "push", "-u", "origin", "feature-branch"], check=True)

    @patch("subprocess.run")
    def test_commit_and_push_changes(self, mock_run):
        utils_git.commit_and_push_changes("feature-branch")
        mock_run.assert_any_call(["git", "add", "."], check=True)
        mock_run.assert_any_call(["git", "commit", "-m", "Upgrade dependencies"], check=True)
        mock_run.assert_any_call(["git", "push", "origin", "feature-branch"], check=True)

    @patch("requests.post")
    def test_create_pull_request(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        utils_git.create_pull_request("user", "repo", "fake_token", "feature-branch")
        mock_post.assert_called_with(
            "https://api.github.com/repos/user/repo/pulls",
            headers={"Authorization": "token fake_token"},
            json={
                "title": "Dependency Upgrade PR",
                "head": "feature-branch",
                "base": "main",
                "body": "This PR upgrades dependencies in pom.xml"
            }
        )

    @patch('shutil.rmtree')
    @patch('os.path.exists')
    def test_remove_repo_if_exists(self, mock_exists, mock_rmtree):
        """Test repository removal functionality"""
    
        # Test when repo exists
        mock_exists.return_value = True
        utils_git.remove_repo_if_exists("/tmp/test", "testrepo")
        mock_rmtree.assert_called_once_with("/tmp/test/testrepo")
        
        # Test when repo doesn't exist
        mock_exists.reset_mock()
        mock_rmtree.reset_mock()
        mock_exists.return_value = False
        utils_git.remove_repo_if_exists("/tmp/test", "testrepo")
        mock_rmtree.assert_not_called()
        
        # Test error handling
        mock_exists.return_value = True
        mock_rmtree.side_effect = Exception("Permission denied")
        with self.assertRaises(ValueError) as context:
            utils_git.remove_repo_if_exists("/tmp/test", "testrepo")
        self.assertIn("Failed to remove existing repository", str(context.exception))   

    
    @patch('git.Repo.clone_from')
    @patch('os.makedirs')
    def test_clone_public_repo_success(self, mock_makedirs, mock_clone):
        """Test successful cloning of a public repository"""
        # Test data
        github_url = "https://github.com/testowner/testrepo"
        target_path = "/tmp/test"
        
        # Execute
        result = utils_git.clone_github_repo(github_url, target_path)
        
        # Assert
        assert result == "/tmp/test/testrepo"
        mock_makedirs.assert_called_once_with(target_path, exist_ok=True)
        mock_clone.assert_called_once_with(
            "https://github.com/testowner/testrepo.git",
            "/tmp/test/testrepo"
        )

    @patch('git.Repo.clone_from')
    @patch('os.makedirs')
    def test_clone_private_repo_with_token(self, mock_makedirs, mock_clone):
        """Test cloning private repository with token"""
        # Test data
        github_url = "https://github.com/testowner/private-repo"
        target_path = "/tmp/test"
        access_token = "ghp_test123token"
        
        # Execute
        result = utils_git.clone_github_repo(github_url, target_path, access_token)
        
        # Assert
        assert result == "/tmp/test/private-repo"
        mock_clone.assert_called_once_with(
            f"https://{access_token}@github.com/testowner/private-repo.git",
            "/tmp/test/private-repo"
        )

    def test_clone_invalid_url(self):
        """Test cloning with invalid GitHub URL"""
        with pytest.raises(ValueError) as exc_info:
            utils_git.clone_github_repo("invalid_url", "/tmp/test")
        assert "Invalid GitHub URL format" in str(exc_info.value)

    @patch('git.Repo.clone_from')
    def test_clone_git_error(self, mock_clone):
        """Test handling of Git clone errors"""
        # Setup mock to raise GitCommandError
        mock_clone.side_effect = GitCommandError('git clone', 128)
        
        with pytest.raises(ValueError) as exc_info:
            utils_git.clone_github_repo("https://github.com/testowner/testrepo", "/tmp/test")
        assert "Failed to clone repository" in str(exc_info.value)

    @patch('os.makedirs')
    def test_clone_directory_creation_error(self, mock_makedirs):
        """Test handling of directory creation errors"""
        # Setup mock to raise OSError
        mock_makedirs.side_effect = OSError("Permission denied")
        
        with pytest.raises(ValueError) as exc_info:
            utils_git.clone_github_repo("https://github.com/testowner/testrepo", "/tmp/test")
        assert "Failed to clone repository" in str(exc_info.value)

    @patch('git.Repo.clone_from')
    @patch('os.makedirs')
    def test_clone_ssh_url(self, mock_makedirs, mock_clone):
        """Test cloning with SSH URL format"""
        # Test data
        github_url = "git@github.com:testowner/testrepo.git"
        target_path = "/tmp/test"
        
        # Execute
        result = utils_git.clone_github_repo(github_url, target_path)
        
        # Assert
        assert result == "/tmp/test/testrepo"
        mock_clone.assert_called_once_with(
            "https://github.com/testowner/testrepo.git",
            "/tmp/test/testrepo"
        )    
    
if __name__ == '__main__':
    unittest.main()
