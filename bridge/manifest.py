# Include the board's default manifest.
include("$(MPY_DIR)/ports/rp2/boards/manifest.py")
# Add packages
#package("lib", base_path="bridge")
package("lib")
# add main
#module("main.py", base_path="bridge")
module("main.py")
