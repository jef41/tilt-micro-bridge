# Include the board's default manifest.
include("$(MPY_DIR)/ports/rp2/boards/RPI_PICO_W/manifest.py")
# Add packages
package("abstractions", base_path="bridge/lib")
package("configuration", base_path="bridge/lib")
package("logging", base_path="bridge/lib")
package("models", base_path="bridge/lib")
package("primitives", base_path="bridge/lib")
package("providers", base_path="bridge/lib")
package("threadsafe", base_path="bridge/lib")
# add modules
module("async_urequests.py", base_path="bridge/lib")
module("bridge_main.py", base_path="bridge/lib")
module("indicator.py", base_path="bridge/lib")
module("time.py", base_path="bridge/lib")
module("wifi_client.py", base_path="bridge/lib")
module("main.py", base_path="bridge")