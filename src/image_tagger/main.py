"""Main program loop."""

import sys
from pathlib import Path

import pandas as pd
from loguru import logger
from PyQt6.QtGui import QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
)
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


class MainWindow(QMainWindow):
    def __init__(
        self,
        image_files: list[Path],
        tags: list[dict[str, str]],
        output_dir: Path,
    ):
        super().__init__()
        self.image_files = image_files
        self.output_dir = output_dir
        self.current_image_index = 0
        self.image_tag_state: dict[Path, dict[str, bool | str]] = {}
        self.tags_by_key: dict[str, str] = {}

        for tag in tags:
            tag_name = tag["name"]
            tag_key = tag["number_keybind"]
            self.tags_by_key[tag_key] = tag_name

        for image_file in self.image_files:
            filename = image_file.name
            folder = image_file.parent
            self.image_tag_state[image_file] = {
                "filename": filename,
                "folder": str(folder),
            }
            # Initialise all tags to False
            for tag_name in self.tags_by_key.values():
                self.image_tag_state[image_file][tag_name] = False

        # UI
        self.image_label = QLabel(self)  # for displaying the image
        self.status_label = QLabel(self)  # for displaying the status (e.g., "Image 1 of 10")
        self.tag_status_label = QLabel(self)  # for displaying the tag status (e.g., "Tag1: True, Tag2: False")
        self.setCentralWidget(self.image_label)  # set the image label as the central widget of the main window

        self.show_current_image()  # show the first image

    def show_current_image(self):
        if self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            pixel_map = QPixmap(str(image_path))
            self.image_label.setPixmap(pixel_map)
            self.status_label.setText(
                f"Image {self.current_image_index + 1} of {len(self.image_files)}: {image_path.name}"
            )
            self.tag_status_label.setText(
                ", ".join(f"{tag}: {self.image_tag_state[image_path][tag]}" for tag in self.tags_by_key.values())
            )
            self.image_label.adjustSize()
            self.status_label.adjustSize()
            self.tag_status_label.adjustSize()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.text().lower()
        # check if it matches a tag keybind
        if key in self.tags_by_key:
            tag_name = self.tags_by_key[key]
            image_path = self.image_files[self.current_image_index]
            # toggle the tag state
            self.image_tag_state[image_path][tag_name] = not self.image_tag_state[image_path][tag_name]
            # re-display the current image to update the tag status
            self.show_current_image()

        # if press right arrow, go to next image
        if event.key() == 16777236:  # right arrow key
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = len(self.image_files) - 1
            self.show_current_image()
        # if press left arrow, go to previous image
        elif event.key() == 16777234:  # left arrow key
            self.current_image_index -= 1
            self.current_image_index = max(self.current_image_index, 0)
            self.show_current_image()


def main():

    # grab the config path from the -c argument
    # check if -c was passed
    if "-c" in sys.argv:
        config_file_path = Path(sys.argv[sys.argv.index("-c") + 1])
        assert config_file_path.exists(), f"Config file does not exist: {config_file_path}"

    else:
        print("Usage: python image_tagger.py -c <config_path>")
        sys.exit(1)

    logger.info(f"config file path: {config_file_path}")

    # load the config file
    with open(config_file_path, "r") as f:
        config = yaml.load(f)
        logger.info(f"loaded config: {config}")

    input_dir_path = Path(config["input_dir"])
    assert input_dir_path.exists(), f"Input directory does not exist: {input_dir_path}"
    output_dir_path = Path(config["output_dir"])
    if not output_dir_path.exists():
        output_dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {output_dir_path}")

    # recursively find all image files in the input directory
    image_files = (
        list(input_dir_path.rglob("*.png")) + list(input_dir_path.rglob("*.jpg")) + list(input_dir_path.rglob("*.jpeg"))
    )
    # make all the image paths relative to the input directory
    image_files = [image_file.relative_to(input_dir_path) for image_file in image_files]
    logger.success(f"Found {len(image_files)} image files in {input_dir_path}")

    # Create the application and window
    app = QApplication(sys.argv)
    window = MainWindow(
        image_files=image_files,
        tags=config["tags"],
        output_dir=output_dir_path,
    )
    window.show()

    # Start the event loop by calling app.exec() and exit the program when the loop ends
    sys.exit(app.exec())
