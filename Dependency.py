class Dependency:
    def __init__(self, group_id, artifact_id, current_version, latest_version="LATEST"):
        self.group_id = group_id
        self.artifact_id = artifact_id
        self.current_version = current_version
        self.latest_version = latest_version

    def get_artifact_version_details(self):
        return {
            "group_id": self.group_id,
            "current_version": self.current_version,
            "latest_version": self.latest_version
        }
    
    def get_artifact_id(self):
        return self.artifact_id

# Creating an instance of the Dependency class
my_dependencies = Dependency("org.springframework.boot","spring-boot-starter-web","2.3.1.RELEASE", "3.4.3")

# Accessing attributes and methods
print(my_dependencies.get_artifact_id())
print(my_dependencies.get_artifact_version_details())