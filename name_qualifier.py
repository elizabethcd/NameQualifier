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
	frameworks = ["spacechase0.JsonAssets", "Pathoschild.ContentPatcher", "DIGUS.CustomCrystalariumMod", "DIGUS.CustomCaskMod", "aedenthorn.CustomOreNodes", "Esca.FarmTypeManager"]
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
						print("Found NPC dispositions patch! Renaming NPCs...")
						for name in patch["Entries"].keys():
							namesDict[name] = modName + name

	# Print out what NPC renaming is going on
	for name in namesDict:
		print("Renaming " + name + " to " + namesDict[name])

	# Run through CP files and strip out old NPC names and replace
	for cpPack in modDict["Pathoschild.ContentPatcher".casefold()]:
		fileList = cpPack.glob("**/*.json")
		for file in fileList:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue
			# Load in the data
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

			# Logging
			print("Everything added by " + str(jaPack.name) + " renamed!")

	# Build context tag dictionaries
	objContextTagDict = {tagify(x):tagify(objectsDict[x]) for x in objectsDict}

	# Go through JA packs and replace item names and NPC names as needed
	for jaPack in modDict["spacechase0.JsonAssets".casefold()]:
		# Replace big craftable recipe ingredients and friendship unlocks as needed
		bigCraftablesPath = jaPack.joinpath("BigCraftables")
		bigCraftablesList = bigCraftablesPath.glob("**/*.json")
		for file in bigCraftablesList:
			newFilePath = get_output_loc(file)
			bcdata = load_json(newFilePath.parent,newFilePath.name)
			# If there is a recipe for the big craftable
			if "Recipe" in bcdata and bcdata["Recipe"] is not None:
				if "Ingredients" in bcdata["Recipe"] and bcdata["Recipe"]["Ingredients"] is not None:
					bcdata["Recipe"]["Ingredients"] = replace_ingreds(bcdata["Recipe"]["Ingredients"], objectsDict)
				# Friendship unlocks
				if "PurchaseRequirements" in bcdata["Recipe"]:
					bcdata["Recipe"]["PurchaseRequirements"] = replace_friend_names(bcdata["Recipe"]["PurchaseRequirements"], namesDict)
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
			if "SeedPurchaseRequirements" in cropdata and cropdata["SeedPurchaseRequirements"] is not None:
				# Regex match any friendship requirements to the names in the names dict
				cropdata["SeedPurchaseRequirements"] = replace_friend_names(cropdata["SeedPurchaseRequirements"], namesDict)
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
			if "SaplingPurchaseRequirements" in treedata and treedata["SaplingPurchaseRequirements"] is not None:
				# Regex match any friendship requirements to the names in the names dict
				treedata["SaplingPurchaseRequirements"] = replace_friend_names(treedata["SaplingPurchaseRequirements"], namesDict)
			save_json(treedata, newFilePath.parent, newFilePath.name)

		# Replace object recipe ingredients and friendship unlocks as needed
		objectsPath = jaPack.joinpath("Objects")
		objectsList = objectsPath.glob("**/*.json")
		for file in objectsList:
			newFilePath = get_output_loc(file)
			objectdata = load_json(newFilePath.parent,newFilePath.name)
			# If there is a recipe for the object
			if "Recipe" in objectdata and objectdata["Recipe"] is not None:
				if "Ingredients" in objectdata["Recipe"] and objectdata["Recipe"]["Ingredients"] is not None:
					objectdata["Recipe"]["Ingredients"] = replace_ingreds(objectdata["Recipe"]["Ingredients"], objectsDict)
				# Friendship unlocks
				if "PurchaseRequirements" in objectdata["Recipe"] and objectdata["Recipe"]["PurchaseRequirements"] is not None:
					# Regex match any friendship requirements to the names in the names dict
					objectdata["Recipe"]["PurchaseRequirements"] = replace_friend_names(objectdata["Recipe"]["PurchaseRequirements"], namesDict)
			# If there are gift tastes from NPCs with new names, replace names
			if "GiftTastes" in objectdata:
				for value in objectdata["GiftTastes"]:
					objectdata["GiftTastes"][value] = [namesDict[person] if person in namesDict else person for person in objectdata["GiftTastes"][value]]
			save_json(objectdata, newFilePath.parent, newFilePath.name)

		# Replace tailoring recipe products (shirts and pants)
		tailoringPath = jaPack.joinpath("Tailoring")
		tailorList = tailoringPath.glob("**/*.json")
		for file in tailorList:
			newFilePath = get_output_loc(file)
			tailordata = load_json(newFilePath.parent,newFilePath.name)
			# Replace crafted items if they're JA shirts or pants
			if "CraftedItems" in tailordata and tailordata["CraftedItems"] is not None:
				tailordata["CraftedItems"] = [shirtsDict[item] if item in shirtsDict else item for item in tailordata["CraftedItems"]]
				tailordata["CraftedItems"] = [pantsDict[item] if item in pantsDict else item for item in tailordata["CraftedItems"]]
			# Replace first item context tags if they're in the objects context tag dict
			if "FirstItemTags" in tailordata and tailordata["FirstItemTags"] is not None:
				tailordata["FirstItemTags"] = [objContextTagDict[tag] if tag in objContextTagDict else tag for tag in tailordata["FirstItemTags"]]
			# Replace second item context tags if they're in the objects context tag dict
			if "SecondItemTags" in tailordata and tailordata["SecondItemTags"] is not None:
				tailordata["SecondItemTags"] = [objContextTagDict[tag] if tag in objContextTagDict else tag for tag in tailordata["SecondItemTags"]]
			save_json(tailordata, newFilePath.parent, newFilePath.name)


		# Replace fence repair material, recipe ingredients, and friendship unlocks
		fencePath = jaPack.joinpath("Fences")
		fenceList = fencePath.glob("**/*.json")
		for file in fenceList:
			newFilePath = get_output_loc(file)
			fencedata = load_json(newFilePath.parent,newFilePath.name)
			if "RepairMaterial" in fencedata and fencedata["RepairMaterial"] is not None and fencedata["RepairMaterial"] in objectsDict:
				fenceData["RepairMaterial"] = objectsDict[fenceData["RepairMaterial"]]
			if "Recipe" in fencedata and fencedata["Recipe"] is not None:
				# Recipe ingredients
				if "Ingredients" in fencedata["Recipe"] and fencedata["Recipe"]["Ingredients"] is not None:
					fencedata["Recipe"]["Ingredients"] = replace_ingreds(fencedata["Recipe"]["Ingredients"], objectsDict)
				# Friendship unlocks
				if "PurchaseRequirements" in fencedata["Recipe"] and fencedata["Recipe"]["PurchaseRequirements"] is not None:
					# Regex match any friendship requirements to the names in the names dict
					fencedata["Recipe"]["PurchaseRequirements"] = replace_friend_names(fencedata["Recipe"]["PurchaseRequirements"], namesDict)
			save_json(fencedata, newFilePath.parent, newFilePath.name)

		# Replace forge recipe inputs and outputs
		forgePath = jaPack.joinpath("Forge")
		forgeList = forgePath.glob("**/*.json")
		for file in forgeList:
			newFilePath = get_output_loc(file)
			forgedata = load_json(file.parent,file.name)
			# Check big craftables
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in bigcraftDict:
				forgedata["BaseItemName"] = bigcraftDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in bigcraftDict:
				forgedata["ResultItemName"] = bigcraftDict[forgedata["ResultItemName"]]
			# Check fences
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in fencesDict:
				forgedata["BaseItemName"] = fencesDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in fencesDict:
				forgedata["ResultItemName"] = fencesDict[forgedata["ResultItemName"]]
			# Check seeds
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in seedDict:
				forgedata["BaseItemName"] = seedDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in seedDict:
				forgedata["ResultItemName"] = seedDict[forgedata["ResultItemName"]]
			# Check saplings
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in saplingDict:
				forgedata["BaseItemName"] = saplingDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in saplingDict:
				forgedata["ResultItemName"] = saplingDict[forgedata["ResultItemName"]]
			# Check shirts
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in shirtsDict:
				forgedata["BaseItemName"] = shirtsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in shirtsDict:
				forgedata["ResultItemName"] = shirtsDict[forgedata["ResultItemName"]]
			# Check pants
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in pantsDict:
				forgedata["BaseItemName"] = pantsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in pantsDict:
				forgedata["ResultItemName"] = pantsDict[forgedata["ResultItemName"]]
			# Check boots
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in bootsDict:
				forgedata["BaseItemName"] = bootsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in bootsDict:
				forgedata["ResultItemName"] = bootsDict[forgedata["ResultItemName"]]
			# Check hats
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in hatsDict:
				forgedata["BaseItemName"] = hatsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in hatsDict:
				forgedata["ResultItemName"] = hatsDict[forgedata["ResultItemName"]]
			# Check objects
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in objectsDict:
				forgedata["BaseItemName"] = objectsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in objectsDict:
				forgedata["ResultItemName"] = objectsDict[forgedata["ResultItemName"]]
			# Check weapons
			if "BaseItemName" in forgedata and forgedata["BaseItemName"] is not None and forgedata["BaseItemName"] in weaponsDict:
				forgedata["BaseItemName"] = weaponsDict[forgedata["BaseItemName"]]
			if "ResultItemName" in forgedata and forgedata["ResultItemName"] is not None and forgedata["ResultItemName"] in weaponsDict:
				forgedata["ResultItemName"] = weaponsDict[forgedata["ResultItemName"]]
			# Check context tags for items, replace if needed
			if "IngredientContextTag" in forgedata and forgedata["IngredientContextTag"] is not None and forgedata["IngredientContextTag"] in objContextTagDict:
				forgedata["IngredientContextTag"] = objContextTagDict[forgedata["IngredientContextTag"]]
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(forgedata, newFilePath.parent, newFilePath.name)

		# Logging
		print("All items and NPCs referenced in " + str(jaPack.name) + " renamed!")

	# Custom Crystalarium Mod
	# Object names for duplication
	for cryPack in modDict["DIGUS.CustomCrystalariumMod".casefold()]:
		allCrystJsons = cryPack.glob("**/*.json")
		for file in allCrystJsons:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue

			crystalData = load_json(file.parent,file.name)
			# Process through each entry in the json list
			for entry in crystalData:
				# Replace the name object names
				if "Name" in entry and entry["Name"] is not None and entry["Name"] in objectsDict:
					entry["Name"] = objectsDict[entry["Name"]]
				# Replace the cloning data object names
				if "CloningData" in entry and entry["CloningData"] is not None:
					clData = entry["CloningData"]
					newData = dict()
					for dat in clData:
						if dat in objectsDict:
							newData[objectsDict[dat]] = clData[dat]
						else:
							newData[dat] = clData[dat]
					entry["CloningData"] = newData

			# Save for later
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(crystalData, newFilePath.parent, newFilePath.name)
		# Logging
		print("All objects referenced in " + str(cryPack.name) + " renamed!")

	# Custom Casks Mod
	# Object names for use in casks
	for caskPack in modDict["DIGUS.CustomCaskMod".casefold()]:
		allCaskJsons = caskPack.glob("**/*.json")
		for file in allCaskJsons:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue

			caskData = load_json(file.parent,file.name)
			caskData = {objectsDict[x] if x in objectsDict else x: caskData[x] for x in caskData}

			# Save for later
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(caskData, newFilePath.parent, newFilePath.name)
		# Logging
		print("All objects referenced in " + str(caskPack.name) + " renamed!")


	# Custom Ore Nodes
	# Object names in ore node produce
	for orePack in modDict["aedenthorn.CustomOreNodes".casefold()]:
		oreJsons = orePack.glob("**/*.json")
		for file in oreJsons:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue

			oreData = load_json(file.parent,file.name)
			# If it's a CON content pack, replace the item names as appropriate
			if "nodes" in oreData and oreData["nodes"] is not None:
				nodeList = oreData["nodes"]
				for oreNode in nodeList:
					if "dropItems" in oreNode and oreNode["dropItems"] is not None:
						dropsList = oreNode["dropItems"]
						for dropItem in dropsList:
							if "itemIdOrName" in dropItem and dropItem["itemIdOrName"] is not None and dropItem["itemIdOrName"] in objectsDict:
								dropItem["itemIdOrName"] = objectsDict[dropItem["itemIdOrName"]]
						oreNode["dropItems"] = dropsList
				oreData["nodes"] = nodeList

			# Save for later
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(oreData, newFilePath.parent, newFilePath.name)
		# Logging
		print("All objects referenced in " + str(orePack.name) + " renamed!")

	# Farm Type Manager
	# Object names for spawning in
	for ftmPack in modDict["Esca.FarmTypeManager".casefold()]:
		ftmJsons = ftmPack.glob("**/*.json")
		for file in ftmJsons:
			# Don't process the manifest (already handled)
			if file.name == "manifest.json":
				continue

			ftmData = load_json(file.parent,file.name)
			if "Forage_Spawn_Settings" in ftmData and ftmData["Forage_Spawn_Settings"] is not None:
				if "Areas" in ftmData["Forage_Spawn_Settings"] and ftmData["Forage_Spawn_Settings"]["Areas"] is not None:
					# Check every season for every entry
					for area in ftmData["Forage_Spawn_Settings"]["Areas"]:
						if "SpringItemIndex" in area and area["SpringItemIndex"] is not None:
							area["SpringItemIndex"] = handle_ftm_area(area["SpringItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
						if "SummerItemIndex" in area and area["SummerItemIndex"] is not None:
							area["SummerItemIndex"] = handle_ftm_area(area["SummerItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
						if "FallItemIndex" in area and area["FallItemIndex"] is not None:
							area["FallItemIndex"] = handle_ftm_area(area["FallItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
						if "WinterItemIndex" in area and area["WinterItemIndex"] is not None:
							area["WinterItemIndex"] = handle_ftm_area(area["WinterItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)

				# Check every season non-area-specific
				if "SpringItemIndex" in ftmData["Forage_Spawn_Settings"] and ftmData["Forage_Spawn_Settings"]["SpringItemIndex"] is not None:
					ftmData["Forage_Spawn_Settings"]["SpringItemIndex"] = handle_ftm_area(ftmData["Forage_Spawn_Settings"]["SpringItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
				if "SummerItemIndex" in ftmData["Forage_Spawn_Settings"] and ftmData["Forage_Spawn_Settings"]["SummerItemIndex"] is not None:
					ftmData["Forage_Spawn_Settings"]["SummerItemIndex"] = handle_ftm_area(ftmData["Forage_Spawn_Settings"]["SummerItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
				if "FallItemIndex" in ftmData["Forage_Spawn_Settings"] and ftmData["Forage_Spawn_Settings"]["FallItemIndex"] is not None:
					ftmData["Forage_Spawn_Settings"]["FallItemIndex"] = handle_ftm_area(ftmData["Forage_Spawn_Settings"]["FallItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
				if "WinterItemIndex" in ftmData["Forage_Spawn_Settings"] and ftmData["Forage_Spawn_Settings"]["WinterItemIndex"] is not None:
					ftmData["Forage_Spawn_Settings"]["WinterItemIndex"] = handle_ftm_area(ftmData["Forage_Spawn_Settings"]["WinterItemIndex"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
			
			# Save for later
			newFilePath = get_output_loc(file)
			newFilePath.parent.mkdir(parents=True, exist_ok=True)
			save_json(ftmData, newFilePath.parent, newFilePath.name)
		# Logging
		print("All objects referenced in " + str(ftmPack.name) + " renamed!")

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
		# print(newName + " processed") # Logging
		# Save json once processed
		newFilePath = get_output_loc(file)
		newFilePath.parent.mkdir(parents=True, exist_ok=True)
		save_json(itemdata, newFilePath.parent, newFilePath.name)

def replace_friend_names(reqList, namesDict):
	def friend_repl(match):
		# If there's a matching name in namesDict, replace it
		if match.group('name') in namesDict:
			return "f " + namesDict[match.group('name')] + " "
		# Otherwise return the whole thing
		else:
			return match.group(0)
	# Do a regex search for friend requirements, replace names if needed
	return [re.sub(r"f (?P<name>[a-zA-Z]+) ", friend_repl, req)  for req in reqList]

def replace_ingreds(ingreds, objectsDict):
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
		if ing["Object"] in objectsDict:
			ing["Object"] = objectsDict[ing["Object"]]
		newIngreds.append(ing)
	return newIngreds

def handle_ftm_area(areaList, objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict):
	for item in areaList:
		# Handle raw integer ID format
		if type(item) is int:
			continue
		# Handle raw string name format
		elif type(item) is str:
			if item in objectsDict:
				item = objectsDict[item]
				continue
		# Handle more complex category-based format
		elif type(item) is dict:
			if "category" in item and item["category"] is not None:
				if item["category"].casefold() == "object":
					# Deal with objects
					if "name" in item:
						item["name"] = objectsDict[item["name"]] if item["name"] in objectsDict else item["name"]
					elif "Name" in item:
						item["Name"] = objectsDict[item["Name"]] if item["Name"] in objectsDict else item["Name"]
				elif item["category"].casefold() == "big craftable":
					# Deal with big craftables
					if "name" in item:
						item["name"] = bigcraftDict[item["name"]] if item["name"] in bigcraftDict else item["name"]
					elif "Name" in item:
						item["Name"] = bigcraftDict[item["Name"]] if item["Name"] in bigcraftDict else item["Name"]
				elif item["category"].casefold() == "boots":
					# Deal with boots
					if "name" in item:
						item["name"] = bootsDict[item["name"]] if item["name"] in bootsDict else item["name"]
					elif "Name" in item:
						item["Name"] = bootsDict[item["Name"]] if item["Name"] in bootsDict else item["Name"]
				elif item["category"].casefold() == "clothing":
					# Deal with clothing
					if "name" in item:
						item["name"] = pantsDict[item["name"]] if item["name"] in pantsDict else item["name"]
						item["name"] = shirtsDict[item["name"]] if item["name"] in shirtsDict else item["name"]
					elif "Name" in item:
						item["Name"] = pantsDict[item["Name"]] if item["Name"] in pantsDict else item["Name"]
						item["Name"] = shirtsDict[item["Name"]] if item["Name"] in shirtsDict else item["Name"]
				elif item["category"].casefold() == "hat":
					# Deal with hats
					if "name" in item:
						item["name"] = hatsDict[item["name"]] if item["name"] in hatsDict else item["name"]
					elif "Name" in item:
						item["Name"] = hatsDict[item["Name"]] if item["Name"] in hatsDict else item["Name"]
				elif item["category"].casefold() == "weapon":
					# Deal with weapons
					if "name" in item:
						item["name"] = weaponsDict[item["name"]] if item["name"] in weaponsDict else item["name"]
					elif "Name" in item:
						item["Name"] = weaponsDict[item["Name"]] if item["Name"] in weaponsDict else item["Name"]
			elif "Category" in item and item["Category"] is not None:
				if item["Category"].casefold() == "object":
					# Deal with objects
					if "name" in item:
						item["name"] = objectsDict[item["name"]] if item["name"] in objectsDict else item["name"]
					elif "Name" in item:
						item["Name"] = objectsDict[item["Name"]] if item["Name"] in objectsDict else item["Name"]
				elif item["Category"].casefold() == "big craftable":
					# Deal with big craftables
					if "name" in item:
						item["name"] = bigcraftDict[item["name"]] if item["name"] in bigcraftDict else item["name"]
					elif "Name" in item:
						item["Name"] = bigcraftDict[item["Name"]] if item["Name"] in bigcraftDict else item["Name"]
				elif item["Category"].casefold() == "boots":
					# Deal with boots
					if "name" in item:
						item["name"] = bootsDict[item["name"]] if item["name"] in bootsDict else item["name"]
					elif "Name" in item:
						item["Name"] = bootsDict[item["Name"]] if item["Name"] in bootsDict else item["Name"]
				elif item["Category"].casefold() == "clothing":
					# Deal with clothing
					if "name" in item:
						item["name"] = pantsDict[item["name"]] if item["name"] in pantsDict else item["name"]
						item["name"] = shirtsDict[item["name"]] if item["name"] in shirtsDict else item["name"]
					elif "Name" in item:
						item["Name"] = pantsDict[item["Name"]] if item["Name"] in pantsDict else item["Name"]
						item["Name"] = shirtsDict[item["Name"]] if item["Name"] in shirtsDict else item["Name"]
				elif item["Category"].casefold() == "hat":
					# Deal with hats
					if "name" in item:
						item["name"] = hatsDict[item["name"]] if item["name"] in hatsDict else item["name"]
					elif "Name" in item:
						item["Name"] = hatsDict[item["Name"]] if item["Name"] in hatsDict else item["Name"]
				elif item["Category"].casefold() == "weapon":
					# Deal with weapons
					if "name" in item:
						item["name"] = weaponsDict[item["name"]] if item["name"] in weaponsDict else item["name"]
					elif "Name" in item:
						item["Name"] = weaponsDict[item["Name"]] if item["Name"] in weaponsDict else item["Name"]
			else:
				print("Malformed spawning area in FTM, no category set!")

			if "Contents" in item:
				# Handle contents list
				area["Contents"] = handle_ftm_area(area["Contents"], objectsDict, bigcraftDict, bootsDict, pantsDict, shirtsDict, hatsDict, weaponsDict)
	return areaList

def tagify(itemname):
	# Trim whitespace (same as game)
	itemname = itemname.strip()
	# Make lowercase (same as game)
	itemname = itemname.lower()
	# Remove spaces (same as game)
	itemname = re.sub(r" ", "_", itemname)
	# Remove apostrophes (same as game)
	itemname = re.sub(r"\'", "", itemname)
	return "item_" + itemname

def load_json(filepath, filename):
	# Read the json in as text
	file_contents = filepath.joinpath(filename).read_text()

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
	with pathname.joinpath(filename).open("w", encoding="utf-8") as write_file:
		json.dump(data, write_file, indent=4, ensure_ascii=False)

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