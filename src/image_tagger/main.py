"""Main program loop."""

import argparse
import sys
from pathlib import Path

import pandas as pd
from loguru import logger
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeyEvent, QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
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

        logger.info(f"Loaded {len(self.image_files)} images from the input directory.")
        if len(self.image_tag_state) > 0:
            logger.info(f"Loaded {len(self.image_tag_state)} images with existing tags from the provided CSV file.")

        # tag initialisation
        self.tags_by_key: dict[str, str] = {tag["number_keybind"].lower(): tag["name"] for tag in tags}
        self.tag_names: list[str] = [tag["name"] for tag in tags]

        logger.info(f"First 10 entries in image tag state: {list(self.image_tag_state.items())[:10]}")

        # image state initialisation
        logger.info(f"Checking for existing tags for {len(self.image_files)} images.")
        num_existing_tags_identified = 0
        for image_path in self.image_files:
            logger.info(f"Checking for existing tags for image: {image_path}")
            # get just the filename from the path without the directory, but include the extension
            if image_path in self.image_tag_state:
                logger.info(f"Found existing tags for image: {image_path}")
                # check that the existing tags in the state match the tags in the config file
                # Check that the base tags are present (filename, folder, tagged)
                existing_tags = self.image_tag_state[image_path]
                if "filename" not in existing_tags:
                    existing_tags["filename"] = image_path.name
                if "folder" not in existing_tags:
                    existing_tags["folder"] = str(image_path.parent)
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
                            f"Extra tag '{tag_name}' found in existing tags for image '{image_path}'. Removing it."
                        )
                        del existing_tags[tag_name]
                num_existing_tags_identified += 1
            else:
                # if the file is not in the existing tags dictionary, add it with default values
                filename = image_path.name
                folder = image_path.parent
                self.image_tag_state[image_path] = {
                    "filename": filename,
                    "folder": str(folder),
                    "tagged": False,
                }
                # Initialise all tags to False
                for tag_name in self.tags_by_key.values():
                    self.image_tag_state[image_path][tag_name] = False

        logger.info(
            f"Initialised {num_existing_tags_identified} images with existing tags from the provided CSV"
            f"file and {len(self.image_files) - num_existing_tags_identified} new images."
        )

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

    def update_status_text(self, image_path: Path):
        untagged = self.get_untagged_images()
        untagged_count = len(untagged)

        first_10_indexes = [index for index, _ in untagged[:10]]
        first_10_text = ", ".join(str(index) for index in first_10_indexes)

        self.status_label.setText(
            f"Image {self.current_image_index} / {len(self.image_files) - 1} : {image_path.name}\n"
            f"Untagged images: {untagged_count} / {len(self.image_files)}\n"
            f"First 10 untagged image indexes: {first_10_text}"
        )

    def update_tag_badges(self):
        state = self.image_tag_state[self.image_files[self.current_image_index]]
        for tag_name in self.tag_badges:
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
            self.update_status_text(image_path)
            # if the image is tagged, render the status label in green
            if self.image_tag_state[image_path]["tagged"]:
                self.status_label.setStyleSheet("color: lime; font-weight: 600;")
            else:
                self.status_label.setStyleSheet("color: white; font-weight: 600;")
            self.update_tag_badges()

    def keyPressEvent(self, a0: QKeyEvent | None) -> None:
        if not a0:
            return
        key = a0.text().lower()
        # check if it matches a tag keybind
        if key in self.tags_by_key:
            tag_name = self.tags_by_key[key]
            image_path = self.image_files[self.current_image_index]
            self.image_tag_state[image_path][tag_name] = not self.image_tag_state[image_path][tag_name]
            self.update_tag_badges()
            self.save_tags_to_csv()
            return

        # if press right arrow, go to next image
        if a0.key() == 16777236:  # right arrow key
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = len(self.image_files) - 1
            self.show_current_image()
        # if press left arrow, go to previous image
        elif a0.key() == 16777234:  # left arrow key
            self.current_image_index -= 1
            self.current_image_index = max(self.current_image_index, 0)
            self.show_current_image()
        # if press enter, mark image as tagged and go to next image
        elif a0.key() == 16777220:  # enter key
            image_path = self.image_files[self.current_image_index]
            self.image_tag_state[image_path]["tagged"] = True
            self.current_image_index += 1
            if self.current_image_index >= len(self.image_files):
                self.current_image_index = len(self.image_files) - 1
            self.save_tags_to_csv()
            self.show_current_image()
        # if press space, leave image as untagged and go to next image
        elif a0.key() == 32:  # space key
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

    def closeEvent(self, a0):
        # save the image_tag_state to a csv file in the output directory
        self.save_tags_to_csv()
        super().closeEvent(a0)

    def get_untagged_images(self) -> list[tuple[int, Path]]:
        """Get a list of untagged image path and their index in the list."""
        untagged_images = []
        for index, image_path in enumerate(self.image_files):
            if not self.image_tag_state[image_path]["tagged"]:
                untagged_images.append((index, image_path))
        return untagged_images


def create_default_config_file(output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"File already exists: {output_path}")
    # Get the default config from the source code
    default_config_path = Path(__file__).parent / "default_config.yaml"
    with open(default_config_path, "r") as f:
        default_config = yaml.load(f)
    with open(output_path, "w") as f:
        yaml.dump(default_config, f)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Image Tagger")
    # Add a command parameter
    sub_parser = parser.add_subparsers(dest="command", required=True)

    # Add subparsers for different commands
    run_parser = sub_parser.add_parser("run", help="Run the image tagger")
    run_parser.add_argument("-c", "--config", type=str, required=True, help="Path to the config file (YAML format)")

    create_config_parser = sub_parser.add_parser("create-config", help="Create a default config file")
    create_config_parser.add_argument(
        "-o", "--output", type=str, required=True, help="Path to save the default config file"
    )

    return parser


def main():

    args = build_argument_parser().parse_args()
    if args.command == "create-config":
        output_path = Path(args.output)
        try:
            create_default_config_file(output_path)
            logger.success(f"Created default config file at {output_path}")
        except FileExistsError as e:
            logger.error(str(e))
            sys.exit(1)
        sys.exit(0)
    elif args.command == "run":
        config_file_path = Path(args.config)
        if not config_file_path.exists():
            logger.error(f"Config file does not exist: {config_file_path}")
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
