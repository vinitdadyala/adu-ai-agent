import unittest
from unittest.mock import patch, Mock
import os
import requests
import utils
from git import Repo, GitCommandError
import pytest

class TestUtils(unittest.TestCase):
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
