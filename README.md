# NameQualifier
Adds qualified names (modAuthor.modName.OriginalName) to a variety of content pack types for Stardew Valley.

## How to Use:

1. Install Python
2. Download source code (big green code button -> download as .zip, unzip)
3. Create `input` folder inside the code folder (same level as the python script)
4. Place content packs for name qualfication inside the `input` folder (JA packs, CP packs, etc)
5. Run the python script by typing `python name_qualifier.py --modName somemodnamehere --modAuthor someauthornamehere` into wherever you run Python, where `somemodnamehere` is replaced with a nice string representing the mod and `someauthornamehere` is replaced with the author name
6. `output` folder is created with converted content packs, ready for use

See https://github.com/elizabethcd/FurnitureConverter/blob/main/README.md#detailed-tutorials-on-how-to-use for more detailed tutorials on running Python scripts for specific operating systems. 

## Not handled

* Any pre-existing i18n formatting (this script assumes your JA packs are all non-localized)
* MFM, MT, MYC, PFM, STF (all coming soon)

There's a lot of rough edges in this script, please ping me on Discord if you run into an issue!
