# NameQualifier
Adds qualified names (modAuthor.modName.OriginalName) to a variety of content pack types for Stardew Valley.

## How to Use:

* Install python 3 of some sort: https://www.python.org/downloads/
* Install the packages used, if needed
  * In a Terminal (Mac or Linux) window, type `pip install json5` and hit return. If you're in Windows, use Powershell and type `py -m pip install json5` instead.
  * Similarly, type `pip install argparse` (or `py -m pip install argparse`) and hit return
  * The other packages used should be default python packages, but if you get errors about that you can try installing the same way
* Download source code (big green code button -> download as .zip, unzip)
* Create `input` folder inside the code folder (same level as the python script)
* Place content packs for name qualfication inside the `input` folder (JA packs, CP packs, etc)
* Use `cd` to navigate into the folder with the python script and the json, or open a terminal window in that folder
   * On a Mac, see the detailed guide for three different ways to do this.
   * On Windows, open File Explorer to the folder you want, click on the address bar, type powershell, and hit return.
   * If you use Linux you can check out info on `cd` for your distro (or see Mac guide)
* Run the python script by typing `python name_qualifier.py --modName somemodnamehere --modAuthor someauthornamehere` into wherever you run Python and hitting return, where `somemodnamehere` is replaced with a nice string representing the mod and `someauthornamehere` is replaced with the author name
* `output` folder is created with converted content packs, ready for use

See https://github.com/elizabethcd/FurnitureConverter/blob/main/README.md#detailed-tutorials-on-how-to-use for more detailed tutorials on running Python scripts for specific operating systems. 

## Not handled

* Any pre-existing i18n formatting (this script assumes your JA packs are all non-localized)
* MFM, MT, MYC, PFM, STF (all coming soon)

There's a lot of rough edges in this script, please ping me on Discord if you run into an issue!
