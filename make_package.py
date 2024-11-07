import os
import subprocess
import zipfile
import shutil
import sys
from pathlib import Path
from site import getsitepackages

def create_lambda_package(package_name
                          , files_to_include
                          , folders_to_include
                          , packages_to_install
                          ,lib_folders_to_include
                          ,create_environment=False
                          ):
    # Create a directory for the Lambda package
    package_dir = Path("lambda_package")
    if package_dir.exists():
        shutil.rmtree(package_dir)  # Clean up any previous package
    package_dir.mkdir()

    # Set up a virtual environment for the dependencies
    if create_environment:
        subprocess.run(["python3", "-m", "venv", package_dir / "venv"], check=False)
        pip_path = package_dir / "venv" / "bin" / "pip"

        # Install the required packages into the package directory
        subprocess.run([pip_path, "install", "--target", str(package_dir), *packages_to_install], check=False)

    # Copy specified files into the package directory
    for file in files_to_include:
        shutil.copy(file, package_dir)

    # Copy specified folders into the package directory
    for folder in folders_to_include:
        shutil.copytree(folder, package_dir / Path(folder).name)
        
    # Locate the site-packages or dist-packages directory
    site_packages_paths = getsitepackages() if hasattr(sys, 'real_prefix') else [Path(sys.prefix) / "lib" / "site-packages"]

    # Copy specified libraries from the environment
    for lib_folder in lib_folders_to_include:
        for site_package in site_packages_paths:
            package_path = Path(site_package) / lib_folder
            if package_path.exists():
                shutil.copytree(package_path, package_dir / lib_folder)
                break
        else:
            print(f"Warning: Package '{lib_folder}' not found in environment.")

    # Create a zip file for the package
    zip_file_path = f"{package_name}.zip"
    with zipfile.ZipFile(zip_file_path, "w", zipfile.ZIP_DEFLATED) as lambda_zip:
        # Add all files in the package directory to the zip file
        for root, _, files in os.walk(package_dir):
            for file in files:
                file_path = Path(root) / file
                lambda_zip.write(file_path, file_path.relative_to(package_dir))

    # Clean up the package directory
    shutil.rmtree(package_dir)

    print(f"Lambda package created: {zip_file_path}")

# Example usage
if __name__ == "__main__":
    package_name = "apigateway_package"
    files_to_include = ["lambda_websocket.py"]
    folders_to_include = ["lib"]
    packages_to_install = ["jwt", "psycopg2"]
    lib_folders_to_include = ["jwt", "psycopg2"]

    create_lambda_package(package_name=package_name
                          , files_to_include=files_to_include
                          , folders_to_include=folders_to_include
                          , packages_to_install=packages_to_install
                          ,lib_folders_to_include=lib_folders_to_include)
