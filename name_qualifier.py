import json
import json5
import re
import argparse
import shutil
from pathlib import Path

inputFolderName = "input"
outputFolderName = "output"

def main():
	# Create the parser
	parser = argparse.ArgumentParser()
	# Add an argument
	parser.add_argument('--modName', type=str, required=True, help="Name of the mod (no spaces), should be identifying")
	parser.add_argument('--modAuthor', type=str, required=True, help="Author of the mod (no spaces)")
	# Parse the argument
	args = parser.parse_args()

	# Initialize input folder
	folderPath = Path(inputFolderName)

	# Set information based on inputs
	modName = args.modName
	modAuthor = args.modAuthor
	# Strip out spaces and punctuation and such from mod author and mod name
	modAuthor = raw_format(modAuthor)
	modName = raw_format(modName)
	uniqueString = modAuthor + "." + modName

	# Use manifest files to find mods in input folder
	modList = []
	jsonAssetsPacks = []
	manifestList = folderPath.glob("**/manifest.json")
	for file in manifestList:
		manifest = load_json(file.parent, "manifest.json")
		# Check that the manifest contains the necessary information
		if not check_manifest(manifest):
			print("Malformed manifest detected, quitting...")
			return
		# Store manifest information if manifest is not bad
		modList.append(file.parent)
		# Copy manifest over
		newFilePath = get_output_loc(file)
		newFilePath.parent.mkdir(parents=True, exist_ok=True)
		save_json(manifest,newFilePath.parent,"manifest.json")
		# Store mod filepath if JA mod detected
		if manifest["ContentPackFor"]["UniqueID"].casefold() == "spacechase0.JsonAssets".casefold():
			jsonAssetsPacks.append(file.parent)
			print("Found JA pack!")

	# Rename items in all JA mods
	bigcraftDict = dict()
	cropDict = dict()
	fruitTreeDict = dict()
	for jaPack in jsonAssetsPacks:
		# Set up i18n for the pack
		i18n = dict()

		# Process Big Craftables
		bigCraftablesPath = jaPack.joinpath("BigCraftables")
		bigCraftablesList = bigCraftablesPath.glob("**/*.json")
		# Rename big craftables
		do_renaming(bigCraftablesList, uniqueString, i18n, bigcraftDict, "bc.", False)
			
		# Process Crops
		cropsPath = jaPack.joinpath("Crops")
		cropsList = cropsPath.glob("**/*.json")
		# Rename crops
		do_renaming(cropsList, uniqueString, i18n, cropDict, "crop.", "Seed")

		# Process Fruit Trees
		fruitTreesPath = jaPack.joinpath("FruitTrees")
		fruitTreesList = fruitTreesPath.glob("**/*.json")
		# Rename fruit trees
		do_renaming(fruitTreesList, uniqueString, i18n, fruitTreeDict, "fruittree.", "Sapling")

		objectPath = jaPack.joinpath("Objects")
		hatsPath = jaPack.joinpath("Hats")
		weaponsPath = jaPack.joinpath("Weapons")
		shirtsPath = jaPack.joinpath("Shirts")
		pantsPath = jaPack.joinpath("Pants")
		bootsPath = jaPack.joinpath("Boots")
		tailoringPath = jaPack.joinpath("Tailoring")
		fencesPath = jaPack.joinpath("Fences")

		# Save i18n file
		save_json(i18n,get_output_loc(jaPack),"i18n/default.json")

	# Save all images to output as-is
	# imageList = folderPath.glob("**/*.png")
	# for file in imageList:
	# 	newFilePath = get_output_loc(file)
	# 	newFilePath.parent.mkdir(parents=True, exist_ok=True)
	# 	shutil.copy(file,newFilePath)
	# print("All .png files copied!")

def do_renaming(fileList, uniqueString, i18n, storingDict, prepender, extras):
	for file in fileList:
		itemdata = load_json(file.parent,file.name)
		newName = uniqueString + '.' + raw_format(itemdata["Name"])
		# Set up translation
		itemdata["TranslationKey"] = prepender + newName
		i18n[prepender + newName + ".name"] = itemdata["Name"]
		# For most things, process the description
		if extras == False:
			i18n[prepender + newName + ".description"] = itemdata["Description"]
		# For crops, process the seed
		if extras == "Seed":
			newSeedName = uniqueString + '.' + raw_format(itemdata["SeedName"])
			itemdata["SeedTranslationKey"] = prepender + newSeedName
			i18n[prepender + newSeedName + ".name"] = itemdata["SeedName"]
			i18n[prepender + newSeedName + ".description"] = itemdata["SeedDescription"]
		# For fruit trees, process the sapling
		if extras == "Sapling":
			newSaplingName = uniqueString + '.' + raw_format(itemdata["SaplingName"])
			itemdata["SaplingTranslationKey"] = prepender + newSaplingName
			i18n[prepender + newSaplingName + ".name"] = itemdata["SaplingName"]
			i18n[prepender + newSaplingName + ".description"] = itemdata["SaplingDescription"]
		# Rename
		itemdata["Name"] = newName
		storingDict[itemdata["Name"]] = newName
		if extras == "Seed":
			itemdata["SeedName"] = newSeedName
			storingDict[itemdata["SeedName"]] = newSeedName
		if extras == "Sapling":
			itemdata["SaplingName"] = newSaplingName
			storingDict[itemdata["SaplingName"]] = newSaplingName
		print(newName + " processed")
		# Save json once processed
		newFilePath = get_output_loc(file)
		newFilePath.parent.mkdir(parents=True, exist_ok=True)
		save_json(itemdata, newFilePath.parent, newFilePath.name)

def load_json(filepath, filename):
	# Read the json in as text
	file_contents = filepath.joinpath(filename).read_text()

	# Some third-party JSON files begin with extraneous characters - try to fix them up.
	unused_chars, opening_bracket, rest_of_file = file_contents.partition("{")
	file_contents = opening_bracket + rest_of_file  # Discard the extra characters.

	# Some JSON files have curly quotes in them, replace them with normal quotes
	file_contents = file_contents.replace(u'\u201c', '"').replace(u'\u201d', '"')

	try:
	    # Try using the standard module first because it's fast and handles most cases.
		data = json.loads(file_contents)
	except json.decoder.JSONDecodeError:
	    # The json5 module is much slower, but is more lenient about formatting issues.
	    try:
	    	data = json5.loads(file_contents)
	    except json.decoder.JSONDecodeError:
	    	data = {}
	    	print("The json file (" + filename + ") specified is not a valid json file. Please try putting it through smapi.io/json and correcting any errors shown there.")

	# Return the data loaded
	return data

def save_json(data, pathname, filename):
	# Make the folder if needed, pulling in relative filepath from filename if needed
	pathname.joinpath(Path(filename).parent).mkdir(exist_ok=True)
	# Save the file
	with pathname.joinpath(filename).open("w") as write_file:
		json.dump(data, write_file, indent=4)

def check_manifest(manifest):
	if "Author" not in manifest:
		print("Author field missing from manifest! Please correct and try again.")
		return False
	if "Name" not in manifest:
		print("Name field missing from manifest! Please correct and try again.")
		return False
	if "Description" not in manifest:
		print("Description field missing from manifest! Please correct and try again.")
		return False
	if "ContentPackFor" not in manifest:
		print("Mod is not a content pack! Please correct and try again.")
		return False
	if "UniqueID" not in manifest["ContentPackFor"]:
		print("Mod does not specify which mod it's a content pack for! Please correct and try again.")
		return False
	return True

def raw_format(name):
	return re.sub(r'[^A-Za-z0-9_\.-]+', '', name)

def get_output_loc(file):
	splitFilePath = list(file.parts)
	splitFilePath[0] = outputFolderName
	return Path("/".join(splitFilePath))

# Call the main() function to actually do things
main()