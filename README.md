# DocXPand tool

## Requirements
* [Python](https://www.python.org/downloads/) 3.9 or 3.10
* [Poetry](https://python-poetry.org/)
* [Chrome](https://www.google.com/chrome/) and the corresponding [webdriver](https://googlechromelabs.github.io/chrome-for-testing/)
* Stable diffusion for face generation, see [stable_diffusion](stable_diffusion/README.md)

## Functionalities

This repository exposes functions to generate documents using templates and generators, contained in [docxpand/templates](docxpand/templates):

* Templates are SVG files, containing information about the appearence of the documents to generate, i.e. their backgrounds, the fields contained in the document, the positions of these fields etc.
* Generators are JSON files, containing information on how to generate the fields content.

This repository allows to :
* Generate documents for known templates ([id_card_td1_a](docxpand/templates/id_card_td1_a), [id_card_td1_b](docxpand/templates/id_card_td1_b), [id_card_td2_a](docxpand/templates/id_card_td2_a), [id_card_td2_b](docxpand/templates/id_card_td2_b), [pp_td3_a](docxpand/templates/pp_td3_a), [pp_td3_b](docxpand/templates/pp_td3_b), [pp_td3_c](docxpand/templates/pp_td3_c), [rp_card_td1](docxpand/templates/rp_card_td1) and [rp_card_td2](docxpand/templates/rp_card_td2) ), by filling the templates with random fake information.
    - These templates are inspired from European ID cards, passports and residence permits. Their format follow the [ISO/IEC 7810
](https://en.wikipedia.org/wiki/ISO/IEC_7810), and they contains machine-readable zone (MRZ) that follow the [Machine Readable Travel Documents Specifications](https://www.icao.int/publications/Documents/9303_p3_cons_en.pdf).  
    - To generate documents, use the [generate_fake_structured_documents.py](scripts/dataset/generate_fake_structured_documents.py) script, that takes as input the name of one of the templates, the number of fake documents to generate, an output directory, an url to request that can serve generated photos of human faces using [stable diffusion](stable_diffusion/README.md), and a [chrome webdriver](https://googlechromelabs.github.io/chrome-for-testing/) corresponding to the installed version of your installed chrome browser.
* Integrate generated document in some scenes, to replace other documents originally present in the scenes.
    - It implies you have some dataset of background scenes usable for this task, with coordinates of original documents to replace by generated fake documents. 
    - To integrate documents, use the [insert_generated_documents_in_scenes.py](scripts/dataset/insert_generated_documents_in_scenes.py) script, that takes as input the directory containing the generated document images, a JSON dataset containing information obout those document images (generated by above script), the directory containing "scene" (background) images, a JSON dataset containing localization information, and an output directory to store the final images. The background scene images must contain images that are present in the [docxpand/specimens](docxpand/specimens) directory. See the [SOURCES.md](docxpand/specimens/SOURCES.md) file for more information.
    - All JSON datasets must follow the `DocFakerDataset` format, defined in [docxpand/dataset.py](docxpand/dataset.py).

### Installation

Run 

    poetry install

### Usage

To generate documents, run:

    poetry run python scripts/generate_fake_structured_documents.py -n <number_to_generate> -o <output_directory> -t <template_to_use> -w <path_to_chrome_driver_path>

To insert document in target images, run:

    poetry run python scripts/insert_generated_documents_in_scenes.py -di <document_images_directory> -dd <documents_dataset> -si <scene_images_directory> -sd <scenes_dataset> -o <output_directory>

# *DocXPand-25k* dataset
The synthetic ID document images dataset ("DocXPand-25k"), released alongside this tool, is licensed under the Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License. To view a copy of this license, visit https://creativecommons.org/licenses/by-nc-sa/4.0/ or send a letter to Creative Commons, PO Box 1866, Mountain View, CA 94042, USA.

You can download the dataset from [this release](https://github.com/QuickSign/docxpand/releases/tag/v1.0.0). It's split into 12 parts (DocXPand-25k.tar.gz.xx, from 00 to 11). Once you've downloaded all 12 binary files, you can extract the content using the following command : `cat DocXPand-25k.tar.gz.* | tar xzvf -`.
The labels are stored in a JSON format, which is readable using the [DocFakerDataset class](https://github.com/QuickSign/docxpand/blob/v1.0.0/docxpand/dataset.py#L276C7-L276C22). The document images are stored in the `images/` folder, which contains one sub-folder per-class. The original image fields (identity photos, ghost images, barcodes, datamatrices) integrated in the documents are stored in the `fields/` sub-folder.
