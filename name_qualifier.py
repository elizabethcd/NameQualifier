import json
import json5
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
	parser.add_argument('--modAuthor', type=str, required=False, help="Author of the mod (no spaces)")
	# Parse the argument
	args = parser.parse_args()

	## Read the manifest json in as text
	folderPath = Path(originalLocation)
	manifest = load_json(folderPath, "manifest.json")
	# Check that the manifest contains the necessary information
	if not check_manifest(manifest):
		print("Malformed manifest, quitting...")
		return

	# Set information based on inputs
	modName = args.modName
	modAuthor = args.modAuthor if args.modAuthor is not None else manifest["Author"]

	# Strip out spaces and punctuation and such from mod author and mod name
	modAuthor = re.sub(r'[^A-Za-z0-9_\.-]+', '', modAuthor)
	modName = re.sub(r'[^A-Za-z0-9_\.-]+', '', modName)
	uniqueString = modAuthor + "." + modName

	# Save all images to output as-is
	imageList = folderPath.glob("*.png")
	for file in filelist:
		print(file)

	# Save all jsons to output with qualified names
	jsonList = folderPath.glob("*.json")


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
	return True

# Call the main() function to actually do things
main()