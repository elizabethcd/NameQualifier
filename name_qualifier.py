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
	parser.add_argument('--doJA', type=str, required=False, default="True", help="Whether or not to qualify JA pack names")
	parser.add_argument('--doNPCs', type=str, required=False, default="True", help="Whether or not to qualify NPC names")
	# Parse the argument
	args = parser.parse_args()

	# Set up input option variables
	processJA = True
	if args.doJA == "False" or args.doJA == "false":
		processJA = False
	elif args.doJA == "True" or args.doJA == "true":
		processJA = True
	else:
		print("Invalid input, defaulting to processing any JA packs included")
	processNPCs = True
	if args.doNPCs == "False" or args.doNPCs == "false":
		processNPCs = False
	elif args.doNPCs == "True" or args.doNPCs == "true":
		processNPCs = True
	else:
		print("Invalid input, defaulting to processing any NPC packs included")

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
	frameworks = ["spacechase0.JsonAssets", "Pathoschild.ContentPatcher", "Esca.FarmTypeManager", "DIGUS.CustomCrystalariumMod"]
	frameworks = [x.casefold() for x in frameworks]
	modDict = {key: [] for key in frameworks}
	manifestList = folderPath.glob("**/manifest.json")
	for file in manifestList:
		manifest = load_json(file.parent, "manifest.json")

		# Check that the manifest contains the necessary information
		if not check_manifest(manifest):
			print("Malformed manifest detected in " + str(file) + ", quitting...")
			return
		# Store manifest information if manifest is not bad
		modList.append(file.parent)

		# Copy manifest over
		newFilePath = get_output_loc(file)
		newFilePath.parent.mkdir(parents=True, exist_ok=True)
		save_json(manifest,newFilePath.parent,"manifest.json")

		# Store mod filepath indexed by framework
		if manifest["ContentPackFor"]["UniqueID"].casefold() in (name.casefold() for name in frameworks):
			modDict[manifest["ContentPackFor"]["UniqueID"].casefold()].append(file.parent)

	# Go through CP mods and find patches matching the following to see what new NPCs there are
	namesDict = dict()
	if processNPCs:
		for cpPack in modDict["Pathoschild.ContentPatcher".casefold()]:
			fileList = cpPack.glob("**/*.json")
			for file in fileList:
				# Don't process the manifest (already handled)
				if file.name == "manifest.json":
					continue
				# Load in the data
				print(str(file))
				cpFileData = load_json(file.parent,file.name)

				# If it's not a CP file, then copy it over
				if "Changes" not in cpFileData:
					newFilePath = get_output_loc(file)
					newFilePath.parent.mkdir(parents=True, exist_ok=True)
					save_json(cpFileData, newFilePath.parent, newFilePath.name)
					continue

				# If it is a CP file, check if it has a dispos patch and process if needed
				changesData = cpFileData["Changes"]
				for patch in changesData:
					if "Target" in patch and patch["Target"].casefold() == "Data/NPCDispositions".casefold() and "Entries" in patch:
						print("Found NPC dispos patch!")
						for name in patch["Entries"].keys():
							namesDict[name] = modName + name

	# Run through CP files and strip out old NPC names and replace
	for cpPack in modDict["Pathoschild.ContentPatcher".casefold()]:
		fileList = cpPack.glob("**/*.json")
		for file in fileList:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue
			# Load in the data
			print(str(file))
			cpFileData = load_json(file.parent,file.name)
			# If it's not a CP file, don't process it
			if "Changes" not in cpFileData:
				continue

			# If it is a CP file, check if it has a dispos patch and process if needed
			changesData = cpFileData["Changes"]
			newChangesData = []
			for patch in changesData:
				# Anything without a Target gets copied
				if "Target" not in patch:
					newChangesData.append(patch)
					continue
				targetName = patch["Target"].casefold()
				# Edit NPC Dispositions patches
				if targetName == "Data/NPCDispositions".casefold() and "Entries" in patch:
					for name in namesDict.keys():
						if name in patch["Entries"]:
							patch["Entries"][namesDict[name]] = patch["Entries"][name]
							del patch["Entries"][name]
					newChangesData.append(patch)
				# Edit Portraits/ patches
				elif targetName.startswith("portraits"):
					for name in namesDict.keys():
						if patch["Target"].casefold().split('/')[1] == name.casefold():
							patch["Target"] = "Portraits/" + namesDict[name]
					newChangesData.append(patch)
				# Edit Characters/ patches
				elif targetName.startswith("characters"):
					restOfTarget = targetName[len("characters/"):]
					for name in namesDict.keys():
						# Sprites
						if restOfTarget == name.casefold():
							patch["Target"] = "Characters/" + namesDict[name]
						# Dialogue
						elif restOfTarget == "dialogue/" + name.casefold():
							patch["Target"] = "Characters/Dialogue/" + namesDict[name]
						# Schedules
						elif restOfTarget == "schedules/" + name.casefold():
							patch["Target"] = "Characters/schedules/" + namesDict[name]
					newChangesData.append(patch)
				# Edit gift taste patches
				elif targetName == "Data/NPCGiftTastes".casefold() and "Entries" in patch:
					for name in namesDict.keys():
						if name in patch["Entries"]:
							patch["Entries"][namesDict[name]] = patch["Entries"][name]
							del patch["Entries"][name]
					newChangesData.append(patch)
				# Edit Custom NPC Exclusions patches
				elif targetName == "Data/CustomNPCExclusions".casefold() and "Entries" in patch:
					for name in namesDict.keys():
						if name in patch["Entries"]:
							patch["Entries"][namesDict[name]] = patch["Entries"][name]
							del patch["Entries"][name]
					newChangesData.append(patch)
				else:
					newChangesData.append(patch)
			cpFileData["Changes"] = newChangesData
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(cpFileData, newFilePath.parent, newFilePath.name)

	# Rename items in all JA mods and store the renaming for later use
	bigcraftDict = dict()
	cropDict = dict()
	seedDict = dict()
	fruitTreeDict = dict()
	saplingDict = dict()
	objectsDict = dict()
	hatsDict = dict()
	weaponsDict = dict()
	shirtsDict = dict()
	pantsDict = dict()
	bootsDict = dict()
	fencesDict = dict()
	if processJA:
		for jaPack in modDict["spacechase0.JsonAssets".casefold()]:
			# Set up i18n for the pack
			i18n = dict()

			# Process Big Craftables
			bigCraftablesPath = jaPack.joinpath("BigCraftables")
			do_renaming(bigCraftablesPath, uniqueString, i18n, bigcraftDict, "bc.", False, False)
				
			# Process Crops
			cropsPath = jaPack.joinpath("Crops")
			do_renaming(cropsPath, uniqueString, i18n, cropDict, "crop.", "Seed", seedDict)

			# Process Fruit Trees
			fruitTreesPath = jaPack.joinpath("FruitTrees")
			do_renaming(fruitTreesPath, uniqueString, i18n, fruitTreeDict, "fruittree.", "Sapling", saplingDict)

			# Process Objects
			objectPath = jaPack.joinpath("Objects")
			do_renaming(objectPath, uniqueString, i18n, objectsDict, "obj.", False, False)

			# Process Hats
			hatsPath = jaPack.joinpath("Hats")
			do_renaming(hatsPath, uniqueString, i18n, hatsDict, "hat.", False, False)

			# Process Weapons
			weaponsPath = jaPack.joinpath("Weapons")
			do_renaming(weaponsPath, uniqueString, i18n, weaponsDict, "weapon.", False, False)

			# Process Shirts
			shirtsPath = jaPack.joinpath("Shirts")
			do_renaming(shirtsPath, uniqueString, i18n, shirtsDict, "shirt.", False, False)

			# Process Pants
			pantsPath = jaPack.joinpath("Pants")
			do_renaming(pantsPath, uniqueString, i18n, pantsDict, "pant.", False, False)

			# Process Boots
			bootsPath = jaPack.joinpath("Boots")
			do_renaming(bootsPath, uniqueString, i18n, bootsDict, "boot.", False, False)

			# Process Fences
			fencesPath = jaPack.joinpath("Fences")
			do_renaming(fencesPath, uniqueString, i18n, fencesDict, "fence.", False, False)

			# Save i18n file
			save_json(i18n,get_output_loc(jaPack),"i18n/default.json")

			print(str(jaPack) + " renamed!")

	for jaPack in modDict["spacechase0.JsonAssets".casefold()]:
		# Replace big craftable recipe ingredients and friendship unlocks as needed
		bigCraftablesPath = jaPack.joinpath("BigCraftables")
		bigCraftablesList = bigCraftablesPath.glob("**/*.json")
		for file in bigCraftablesList:
			newFilePath = get_output_loc(file)
			bcdata = load_json(newFilePath.parent,newFilePath.name)
			# If there is a recipe for the big craftable
			if "Recipe" in bcdata:
				ingreds = bcdata["Recipe"]["Ingredients"]
				newIngreds = []
				for ing in ingreds:
					# Case sensitivity my nemesis
					if "Object" not in ing:
						if "object" in ing:
							ing["Object"] = ing["object"]
							del ing["object"]
						else:
							print("Recipe ingredient missing an object!")
							continue
					# Replace object names
					if ing["Object"] in objectsDict.keys():
						ing["Object"] = objectsDict[ing["Object"]]
					newIngreds.append(ing)
				bcdata["Recipe"]["Ingredients"] = newIngreds
				# Friendship unlocks
				if "PurchaseRequirements" in bcdata["Recipe"]:
					reqList = bcdata["Recipe"]["PurchaseRequirements"]
					newReqList = []
					for req in reqList:
						for name in namesDict:
							if "f " + name in req:
								req.replace("f " + name, "f " + namesDict[name])
						newReqList.append(req)
					bcdata["Recipe"]["PurchaseRequirements"] = newReqList
				save_json(bcdata, newFilePath.parent, newFilePath.name)

		# Replace crop products and friendship unlocks as needed
		cropsPath = jaPack.joinpath("Crops")
		cropsList = cropsPath.glob("**/*.json")
		for file in cropsList:
			newFilePath = get_output_loc(file)
			cropdata = load_json(newFilePath.parent,newFilePath.name)
			# Crop product object names
			if cropdata["Product"] in objectsDict.keys():
				cropdata["Product"] = objectsDict[cropdata["Product"]]
			# Friendship unlocks
			if "SeedPurchaseRequirements" in cropdata:
					reqList = cropdata["SeedPurchaseRequirements"]
					newReqList = []
					if reqList is not None:
						for req in reqList:
							for name in namesDict:
								if "f " + name in req:
									req = req.replace("f " + name, "f " + namesDict[name])
							newReqList.append(req)
						cropdata["SeedPurchaseRequirements"] = newReqList
			save_json(cropdata, newFilePath.parent, newFilePath.name)

		# Replace fruit tree products and friendship unlocks as needed
		fruitTreesPath = jaPack.joinpath("FruitTrees")
		fruitTreesList = fruitTreesPath.glob("**/*.json")
		for file in fruitTreesList:
			newFilePath = get_output_loc(file)
			treedata = load_json(newFilePath.parent,newFilePath.name)
			# Fruit tree product object names
			if treedata["Product"] in objectsDict.keys():
				treedata["Product"] = objectsDict[treedata["Product"]]
			# Friendship unlocks
			if "SaplingPurchaseRequirements" in treedata:
					reqList = treedata["SaplingPurchaseRequirements"]
					newReqList = []
					if reqList is not None:
						for req in reqList:
							for name in namesDict:
								if "f " + name in req:
									req = req.replace("f " + name, "f " + namesDict[name])
							newReqList.append(req)
						treedata["SaplingPurchaseRequirements"] = newReqList
			save_json(treedata, newFilePath.parent, newFilePath.name)

	# Go through JA mods and replace all renamed item names and NPC names
	# Objects: recipe ingredients
	# Tailoring recipe: crafted item
	# Fences: recipe ingredients
	# Forge recipes: BaseItemName and ResultItemName
	# NPC names:
	# Friendship purchase requirements
	# Gift tastes

	# Custom Crystalarium Mod
	# Object names for duplication

	# Custom Casks Mod
	# Object names for use in casks

	# Custom Ore Nodes
	# Object names in ore node produce

	# Farm Type Manager
	# Object names for spawning

	# Mail Framework Mod
	# Names of items attached to mail

	# Miller Time
	# Object Names in milling recipes

	# Multi Yield Crops
	# Crops names
	# Extra produce names

	# Producer Framework Mod
	# Big craftables for producer names
	# Objects for input and output names

	# Shop Tile Framework
	# Object names to be sold
	# Big craftable names to be sold
	# NPC friendship requirements

	# Save all images and maps to output as-is
	if False:
		imageList = folderPath.glob("**/*.png")
		for file in imageList:
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy(file,newFilePath)
		print("All .png files copied!")

		mapList = folderPath.glob("**/*.tmx")
		for file in mapList:
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy(file,newFilePath)
		print("All .tmx files copied!")

		mapList = folderPath.glob("**/*.tbin")
		for file in mapList:
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			shutil.copy(file,newFilePath)
		print("All .tbin files copied!")

def do_renaming(filePath, uniqueString, i18n, storingDict, prepender, extras, extrasDict):
	fileList = filePath.glob("**/*.json")
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
		storingDict[itemdata["Name"]] = newName
		itemdata["Name"] = newName
		if extras == "Seed":
			storingDict[itemdata["SeedName"]] = newSeedName
			itemdata["SeedName"] = newSeedName
		if extras == "Sapling":
			storingDict[itemdata["SaplingName"]] = newSaplingName
			itemdata["SaplingName"] = newSaplingName
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

	# Some files have newlines inside strings, this causes problems
	file_contents = file_contents.replace('\n"','"')
	file_contents = file_contents.replace('\r"','"')

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