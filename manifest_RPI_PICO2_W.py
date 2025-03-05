# Include the board's default manifest.
include("$(MPY_DIR)/ports/rp2/boards/RPI_PICO2_W/manifest.py")
# Add packages
package("abstractions", base_path="lib")
package("configuration", base_path="lib")
package("logging", base_path="lib")
package("models", base_path="lib")
package("primitives", base_path="lib")
package("providers", base_path="lib")
package("threadsafe", base_path="lib")
# add modules
module("async_urequests.py", base_path="lib")
module("bridge_main.py", base_path="lib")
module("indicator.py", base_path="lib")
module("time.py", base_path="lib")
module("wifi_client.py", base_path="lib")
module("main.py")
#require("bundle-networking")