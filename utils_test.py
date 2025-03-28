import unittest
from unittest.mock import patch, Mock
from utils import parse_github_url, fetch_github_file, parse_pom, get_latest_version, fetch_latest_versions
import os
import requests
import xml.etree.ElementTree as ET
import concurrent.futures

class TestUtils(unittest.TestCase):
    def test_parse_github_url_valid_https(self):
        url = "https://github.com/testowner/testrepo"
        owner, repo = parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_ssh(self):
        url = "git@github.com:testowner/testrepo.git" 
        owner, repo = parse_github_url(url)
        self.assertEqual(owner, "testowner")
        self.assertEqual(repo, "testrepo")

    def test_parse_github_url_valid_short(self):
        url = "testowner/testrepo"
        owner, repo = parse_github_url(url)
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
                parse_github_url(url)

    @patch('requests.get')
    def test_fetch_github_file_success(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = "test content"
        mock_get.return_value = mock_response

        content = fetch_github_file("owner", "repo", "test.xml", "token123")
        self.assertEqual(content, "test content")
        mock_get.assert_called_with(
            "https://raw.githubusercontent.com/owner/repo/main/test.xml",
            headers={
                "Authorization": "Bearer token123",
                "Accept": "application/vnd.github.v3.raw"
            }
        )

    @patch('requests.get')
    def test_fetch_github_file_error(self, mock_get):
        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        mock_get.return_value = mock_response

        with self.assertRaises(Exception):
            fetch_github_file("owner", "repo", "test.xml", "token123")

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

        dependencies = parse_pom("test_pom.xml")
        
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

        version = get_latest_version("org.test", "test-artifact")
        self.assertEqual(version, "2.1.0")

    @patch('requests.get')
    def test_get_latest_version_timeout(self, mock_get):
        mock_get.side_effect = requests.RequestException()
        version = get_latest_version("org.test", "test-artifact")
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
            
            updated_deps = fetch_latest_versions(test_dependencies)
            
            self.assertEqual(updated_deps["test-artifact"]["latest_version"], "1.1.0")
            self.assertEqual(updated_deps["test-artifact2"]["latest_version"], "2.1.0")

if __name__ == '__main__':
    unittest.main()
