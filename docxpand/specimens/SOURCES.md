# Specimens
This directory must contain specimens of documents present in the original images (scenes). For our paper, we mainly use driving licenses, identity cards, passport and residence permits that have been obtained on the [PRADO](https://www.consilium.europa.eu/prado/) website. We convert them in jpeg format. However, we have no right to distribute or duplicate any materials contained on the PRADO section as expressed in the [COPYRIGHT](https://www.consilium.europa.eu/en/about-site/copyright/).

These specimens are used mainly to estimate color shift and lighting variations to be applied to the synthetically generated document images.

To use our code base, you will have to download them, rename them, convert them in jpeg format and put them in this directory by your own means. 
The naming convention we used is the following : `specimen_path = os.path.join(SPECIMENS_DIR,f"{specimen_name.lower().replace('_', '-')}.jpg")`, e.g. if the class used in the orginal dataset is "ID_CARD_FRA_2021_FRONT", the name of the specimen image must be "id-card-fra-2021-front.jpg".

# Photos
The sub-folder "photos" contains example photos to control the pose of generated faces using stable diffusion. The sources and license of these photos are described in "photos/SOURCES.md".

