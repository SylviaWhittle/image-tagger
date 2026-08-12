"""Main program loop."""

import sys
from pathlib import Path

import pandas as pd
from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QFrame,
)
from ruamel.yaml import YAML

yaml = YAML(typ="safe")


class MainWindow(QMainWindow):
    def __init__(
        self,
        image_files: list[Path],
        tags: list[dict[str, str]],
        output_dir: Path,
        image_tag_state: dict[Path, dict[str, bool | str]],
    ):
        super().__init__()
        self.image_files = image_files
        self.output_dir = output_dir
        self.current_image_index = 0
        self.image_tag_state = image_tag_state

        assert len(tags) > 0, "No tags provided in the config file."
        assert len(tags) <= 10, "Too many tags to handle currently. Ask for more to be supported."

        # tag initialisation
        self.tags_by_key: dict[str, str] = {tag["number_keybind"].lower(): tag["name"] for tag in tags}
        self.tag_names: list[str] = [tag["name"] for tag in tags]

        # image state initialisation
        logger.info(f"Checking for existing tags for {len(self.image_files)} images.")
        for image_file in self.image_files:
            if image_file in self.image_tag_state:
                # check that the existing tags in the state match the tags in the config file
                # Check that the base tags are present (filename, folder, tagged)
                existing_tags = self.image_tag_state[image_file]
                if "filename" not in existing_tags:
                    existing_tags["filename"] = image_file.name
                if "folder" not in existing_tags:
                    existing_tags["folder"] = str(image_file.parent)
                if "tagged" not in existing_tags:
                    existing_tags["tagged"] = False
                # Check that all tags in the config file are present in the existing tags
                for tag_name in self.tag_names:
                    if tag_name not in existing_tags:
                        existing_tags[tag_name] = False
                # Check that there are no extra tags in the existing tags that are not in the config
                for tag_name in list(existing_tags.keys()):
                    if tag_name not in self.tag_names and tag_name not in ["filename", "folder", "tagged"]:
                        logger.warning(
                            f"Extra tag '{tag_name}' found in existing tags for image '{image_file}'. Removing it."
                        )
                        del existing_tags[tag_name]
            else:
                filename = image_file.name
                folder = image_file.parent
                self.image_tag_state[image_file] = {
                    "filename": filename,
                    "folder": str(folder),
                    "tagged": False,
                }
                # Initialise all tags to False
                for tag_name in self.tags_by_key.values():
                    self.image_tag_state[image_file][tag_name] = False

        # UI
        root = QWidget()  # root widget for main window
        root_layout = QHBoxLayout(root)  # horizontal layout for root widget
        root_layout.setContentsMargins(10, 10, 10, 10)  # set margins for the layout
        root_layout.setSpacing(10)

        # left tag column
        self.tag_panel = QFrame(root)  # left panel for displaying the tags
        self.tag_panel.setFixedWidth(260)
        tag_layout = QVBoxLayout(self.tag_panel)  # vertical layout for the tag panel
        tag_layout.setSpacing(8)

        self.tag_badges: dict[str, QLabel] = {}
        for tag in tags:
            tag_name = tag["name"]
            tag_keybind = tag["number_keybind"]
            tag_label = QLabel(f"{tag_name} ({tag_keybind})", self.tag_panel)
            tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tag_label.setStyleSheet("border: 1px solid #000; font-weight: 600;")
            self.tag_badges[tag_name] = tag_label
            tag_layout.addWidget(tag_label)

        tag_layout.addStretch()  # add stretch to push the tags to the top

        # Right column
        right = QWidget(root)  # right panel for displaying the image and status
        right_layout = QVBoxLayout(right)  # vertical layout for the right panel
        right_layout.setSpacing(8)

        self.image_label = QLabel(right)
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label = QLabel(right)

        right_layout.addWidget(
            self.image_label, 1
        )  # add the image label with stretch factor 1 to take up remaining space
        right_layout.addWidget(self.status_label, 0)  # and the status label too but without stretch
        # so it doesn't take up too much space

        root_layout.addWidget(self.tag_panel)
        root_layout.addWidget(right)

        self.setCentralWidget(root)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)  # set focus policy to accept key events
        # otherwise the keyPressEvent won't be called

        self.show_current_image()  # show the first image

    def update_tag_badges(self):
        state = self.image_tag_state[self.image_files[self.current_image_index]]
        for tag_name, tag_label in self.tag_badges.items():
            if state[tag_name]:
                self.tag_badges[tag_name].setStyleSheet(
                    "background: #fff; color: #000; border: 1px solid #000; font-weight: 700;"
                )
            else:
                self.tag_badges[tag_name].setStyleSheet(
                    "background: #000; color: #fff; border: 1px solid #000; font-weight: 700;"
                )

    def show_current_image(self):
        if self.current_image_index < len(self.image_files):
            image_path = self.image_files[self.current_image_index]
            pixel_map = QPixmap(str(image_path))
            self.image_label.setPixmap(pixel_map)
            self.status_label.setText(
                f"Image {self.current_image_index + 1}/{len(self.image_files)}: {image_path.name}"
            )
            # if the image is tagged, render the status label in green
            if self.image_tag_state[image_path]["tagged"]:
                self.status_label.setStyleSheet("color: lime; font-weight: 600;")
            else:
                self.status_label.setStyleSheet("color: white; font-weight: 600;")
            self.update_tag_badges()

    def keyPressEvent(self, event: QKeyEvent):
        key = event.text().lower()
        # check if it matches a tag keybind
        if key in self.tags_by_key:
            tag_name = self.tags_by_key[key]
            image_path = self.image_files[self.current_image_index]
            self.image_tag_state[image_path][tag_name] = not self.image_tag_state[image_path][tag_name]
            self.update_tag_badges()
            self.save_tags_to_csv()
            return

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
        # if press enter, mark image as tagged and go to next image
        elif event.key() == 16777220:  # enter key
            image_path = self.image_files[self.current_image_index]
            self.image_tag_state[image_path]["tagged"] = True
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = len(self.image_files) - 1
            self.save_tags_to_csv()
            self.show_current_image()
        # if press space, leave image as untagged and go to next image
        elif event.key() == 32:  # space key
            image_path = self.image_files[self.current_image_index]
            self.image_tag_state[image_path]["tagged"] = False
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = len(self.image_files) - 1
            self.save_tags_to_csv()
            self.show_current_image()

    def save_tags_to_csv(self):
        # save the image_tag_state to a csv file in the output directory
        output_file_path = self.output_dir / "image_tags.csv"
        df = pd.DataFrame.from_dict(self.image_tag_state, orient="index")
        df.to_csv(output_file_path)

    def closeEvent(self, event):
        # save the image_tag_state to a csv file in the output directory
        self.save_tags_to_csv()
        super().closeEvent(event)


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

    # If an existing tags csv is provided, load it and use that
    if config.get("existing_tags_csv"):
        existing_tags_csv_path = Path(config["existing_tags_csv"])
        if existing_tags_csv_path.exists():
            logger.info(f"Loading existing tags from {existing_tags_csv_path}")
            df_existing_tags = pd.read_csv(existing_tags_csv_path, index_col=0)
            # Convert to path
            df_existing_tags.index = df_existing_tags.index.map(Path)
            # convert the dataframe to a dict of dicts
            image_tag_state = df_existing_tags.to_dict(orient="index")
        else:
            logger.warning(f"Existing tags csv does not exist: {existing_tags_csv_path}")
            image_tag_state = {}
    else:
        image_tag_state = {}

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
        image_files=image_files, tags=config["tags"], output_dir=output_dir_path, image_tag_state=image_tag_state
    )
    window.show()

    # Start the event loop by calling app.exec() and exit the program when the loop ends
    sys.exit(app.exec())
