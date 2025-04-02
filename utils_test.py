import unittest
from unittest.mock import patch, Mock
import os
import requests
import utils
from git import Repo, GitCommandError
import pytest

class TestUtils(unittest.TestCase):
    def test_parse_github_url_valid_https(self):
        url = "https://github.com/testowner/testrepo"
        owner, repo = utils.parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_ssh(self):
        url = "git@github.com:testowner/testrepo.git" 
        owner, repo = utils.parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_short(self):
        url = "testowner/testrepo"
        owner, repo = utils.parse_github_url(url)
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
                utils.parse_github_url(url)

    def test_parse_pom_with_dependencies(self):
        test_pom_content = """
        <project xmlns="http://maven.apache.org/POM/4.0.0">
            <dependencies>
                <dependency>
                    <groupId>org.test</groupId>
                    <artifactId>test-artifact</artifactId>
                    <version>1.0.0</version>
                </dependency>
                <dependency>
                    <groupId>org.test2</groupId>
                    <artifactId>test-artifact2</artifactId>
                </dependency>
            </dependencies>
        </project>
        """
        with open("test_pom.xml", "w") as f:
            f.write(test_pom_content)

        dependencies = utils.parse_pom("test_pom.xml")
        
        self.assertEqual(len(dependencies), 2)
        self.assertEqual(dependencies["test-artifact"]["group_id"], "org.test")
        self.assertEqual(dependencies["test-artifact"]["current_version"], "1.0.0")
        self.assertEqual(dependencies["test-artifact2"]["current_version"], "LATEST")

        os.remove("test_pom.xml")

    @patch('requests.get')
    def test_get_latest_version_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = """
        <metadata>
            <versioning>
                <latest>2.1.0</latest>
            </versioning>
        </metadata>
        """.encode()
        mock_get.return_value = mock_response

        version = utils.get_latest_version("org.test", "test-artifact")
        self.assertEqual(version, "2.1.0")

    @patch('requests.get')
    def test_get_latest_version_timeout(self, mock_get):
        mock_get.side_effect = requests.RequestException()
        version = utils.get_latest_version("org.test", "test-artifact")
        self.assertEqual(version, "UNKNOWN")

    def test_fetch_latest_versions(self):
        test_dependencies = {
            "test-artifact": {
                "group_id": "org.test",
                "current_version": "1.0.0"
            },
            "test-artifact2": {
                "group_id": "org.test2",
                "current_version": "2.0.0"
            }
        }

        with patch('utils.get_latest_version') as mock_get_latest:
            mock_get_latest.side_effect = ["1.1.0", "2.1.0"]
            
            updated_deps = utils.fetch_latest_versions(test_dependencies)
            
            self.assertEqual(updated_deps["test-artifact"]["latest_version"], "1.1.0")
            self.assertEqual(updated_deps["test-artifact2"]["latest_version"], "2.1.0")

    @patch("subprocess.run")
    def test_branch_exists(self, mock_run):
        mock_run.return_value = Mock(stdout="  origin/main\n  origin/dev")
        self.assertTrue(utils.branch_exists("main"))
        self.assertFalse(utils.branch_exists("feature-branch"))

    @patch("subprocess.run")
    def test_create_branch(self, mock_run):
        with patch("utils.branch_exists", return_value=False):
            utils.create_branch("feature-branch")
            mock_run.assert_any_call(["git", "checkout", "-b", "feature-branch"], check=True)
            mock_run.assert_any_call(["git", "push", "-u", "origin", "feature-branch"], check=True)

    @patch("subprocess.run")
    def test_commit_and_push_changes(self, mock_run):
        utils.commit_and_push_changes("feature-branch")
        mock_run.assert_any_call(["git", "add", "."], check=True)
        mock_run.assert_any_call(["git", "commit", "-m", "Upgrade dependencies"], check=True)
        mock_run.assert_any_call(["git", "push", "origin", "feature-branch"], check=True)

    @patch("requests.post")
    def test_create_pull_request(self, mock_post):
        mock_response = Mock()
        mock_response.status_code = 201
        mock_post.return_value = mock_response
        utils.create_pull_request("user", "repo", "fake_token", "feature-branch")
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

    
    @patch('git.Repo.clone_from')
    @patch('os.makedirs')
    def test_clone_public_repo_success(self, mock_makedirs, mock_clone):
        """Test successful cloning of a public repository"""
        # Test data
        github_url = "https://github.com/testowner/testrepo"
        target_path = "/tmp/test"
        
        # Execute
        result = utils.clone_github_repo(github_url, target_path)
        
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
        result = utils.clone_github_repo(github_url, target_path, access_token)
        
        # Assert
        assert result == "/tmp/test/private-repo"
        mock_clone.assert_called_once_with(
            f"https://{access_token}@github.com/testowner/private-repo.git",
            "/tmp/test/private-repo"
        )

    def test_clone_invalid_url(self):
        """Test cloning with invalid GitHub URL"""
        with pytest.raises(ValueError) as exc_info:
            utils.clone_github_repo("invalid_url", "/tmp/test")
        assert "Invalid GitHub URL format" in str(exc_info.value)

    @patch('git.Repo.clone_from')
    def test_clone_git_error(self, mock_clone):
        """Test handling of Git clone errors"""
        # Setup mock to raise GitCommandError
        mock_clone.side_effect = GitCommandError('git clone', 128)
        
        with pytest.raises(ValueError) as exc_info:
            utils.clone_github_repo("https://github.com/testowner/testrepo", "/tmp/test")
        assert "Failed to clone repository" in str(exc_info.value)

    @patch('os.makedirs')
    def test_clone_directory_creation_error(self, mock_makedirs):
        """Test handling of directory creation errors"""
        # Setup mock to raise OSError
        mock_makedirs.side_effect = OSError("Permission denied")
        
        with pytest.raises(ValueError) as exc_info:
            utils.clone_github_repo("https://github.com/testowner/testrepo", "/tmp/test")
        assert "Failed to clone repository" in str(exc_info.value)

    @patch('git.Repo.clone_from')
    @patch('os.makedirs')
    def test_clone_ssh_url(self, mock_makedirs, mock_clone):
        """Test cloning with SSH URL format"""
        # Test data
        github_url = "git@github.com:testowner/testrepo.git"
        target_path = "/tmp/test"
        
        # Execute
        result = utils.clone_github_repo(github_url, target_path)
        
        # Assert
        assert result == "/tmp/test/testrepo"
        mock_clone.assert_called_once_with(
            "https://github.com/testowner/testrepo.git",
            "/tmp/test/testrepo"
        )    

    @patch('os.path.isfile')
    def test_file_exists(self, mock_isfile):
        """Test file existence checking"""
        
        # Test existing file
        mock_isfile.return_value = True
        self.assertTrue(utils.file_exists("pom.xml"))
        
        # Test non-existing file
        mock_isfile.return_value = False
        self.assertFalse(utils.file_exists("nonexistent.xml"))
        
        # Test error handling
        mock_isfile.side_effect = Exception("Test error")
        self.assertFalse(utils.file_exists("error.xml"))    

if __name__ == '__main__':
    unittest.main()
