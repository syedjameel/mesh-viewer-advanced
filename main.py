from ui.main_application_refactored import MainApplication
from utils.async_task import TaskManager

# Create a global task manager instance
task_manager = TaskManager()

if __name__ == "__main__":
    app = MainApplication(task_manager)
    app.run()