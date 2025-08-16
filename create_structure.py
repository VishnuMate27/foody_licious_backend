import os

structure = {
    "app": {
        "__init__.py": "",
        "models": {
            "__init__.py": "",
            "user.py": "",
            "restaurant.py": "",
            "item.py": "",
            "menu.py": "",
            "order.py": "",
            "feedback.py": "",
        },
        "repositories": {
            "__init__.py": "",
            "base_repository.py": "",
            "user_repository.py": "",
            "restaurant_repository.py": "",
            "item_repository.py": "",
            "menu_repository.py": "",
            "order_repository.py": "",
            "feedback_repository.py": "",
        },
        "services": {
            "__init__.py": "",
            "auth_service.py": "",
            "user_service.py": "",
            "restaurant_service.py": "",
            "item_service.py": "",
            "menu_service.py": "",
            "order_service.py": "",
            "feedback_service.py": "",
        },
        "controllers": {
            "__init__.py": "",
            "auth_controller.py": "",
            "user_controller.py": "",
            "restaurant_controller.py": "",
            "item_controller.py": "",
            "menu_controller.py": "",
            "order_controller.py": "",
            "feedback_controller.py": "",
        },
        "middleware": {
            "__init__.py": "",
            "auth_middleware.py": "",
            "error_handler.py": "",
        },
        "utils": {
            "__init__.py": "",
            "database.py": "",
            "firebase_config.py": "",
            "validators.py": "",
            "helpers.py": "",
        },
        "config": {
            "__init__.py": "",
            "settings.py": "",
        },
    },
    "requirements.txt": "",
    ".env": "",
    ".gitignore": "",
    "run.py": "",
    "README.md": "",
}

def create_structure(base_path, structure):
    for name, content in structure.items():
        path = os.path.join(base_path, name)
        if isinstance(content, dict):
            os.makedirs(path, exist_ok=True)
            create_structure(path, content)
        else:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    base_directory = os.getcwd()  # Or change this to another desired path
    create_structure(base_directory, structure)
    print("✅ Project structure created.")
