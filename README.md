# image-tagger

## installation

- Ensure you have the right python version installed in a virtual environment.
- Install via pip:
```bash
pip install git+https://github.com/SylviaWhittle/image-tagger.git
```

## Usage

Images are shown sequentially, you can tag them with tags that you specify in the config file, and then mark the 
image as tagged.

The output will be saved in a `.csv` file - `image_tags.csv` as you go. All images have a `tagged` tag, which lets
you know if they've been tagged.

### Running the software

A config file is required, pass it using the `-c` argument.

```bash
image-tagger run -c my_config_file.yaml
```

### Controls
- enter : flag this image as having been tagged - the name will then show up in green.
- space : flag this image as not having been tagged - the name will then show up in white.
- keys 0-9 : for tagging images.
- arrow keys <- -> : for moving forwards and backwards through the images.

### Creating a new config file
```bash
image-tagger create-config -o ./my_config.yaml
```

### Finishing up
When done, just quit using the X button in the corner - the state is saved as you go.

### Tags
- Tags are currently only binary - true or false.
- Planning on adding support for tagging with numbers later.

### Config file
- Use it to set custom tags by adding rows, following the format:
```yaml
- name: my_tag_name
  number_keybind: "1"
```

Any questions, just holler.
