# GLOBAL MODULES
import queue, threading, importlib, os, sqlite3, json
from pathlib import Path

# LOCAL MODULES
from core_modules import server, message_processor, initializer
import client

def load_plugins(app, plugin_dir="plugins"):
    for filename in os.listdir(plugin_dir):
        if filename.endswith(".py") and not filename.startswith("__"):
            module_name = filename[:-3]
            module_path = f"{plugin_dir}.{module_name}".replace("/", ".")
            try:
                module = importlib.import_module(module_path)
                if hasattr(module, "init"):
                    threading.Thread(target=module.init, args=(app,)).start()
                    print(f"Loaded plugin: {module_name}")
                else:
                    print(f"Failed to load {module_name}: no init(app) function.")
            except Exception as e:
                print(f"Failed to load {module_name}: {e}")

def load_modules(app, modules_dir="modules"):
    for module_name in app.config["modules"].keys():
        if app.config["modules"][module_name]:
            try:
                module = importlib.import_module(f"modules.{module_name}")
                if hasattr(module, "init"):
                    threading.Thread(target=module.init, args=(app,)).start()
                    print(f"Loaded plugin: {module_name}")
                else:
                    print(f"Failed to load {module_name}: no init(app) function.")
            except Exception as e:
                print(f"Failed to load {module_name}: {e}")

class App:
    def __init__(self):
        self.ready = threading.Event()
        self.key = queue.Queue()

        self.global_private = None

        self.state = "full-ready"

        self.received_message_queue = queue.Queue()
        self.server_connection_queues = dict()
        self.core_database_path = "db/core.db"

        self.processed_messages_pool = queue.Queue()
        self.already_emited = set()

        self.addresses = dict()

        self.protocol_version = 1

        self.pow_target = int(str("ff"*32), 16)

        with open("src/config.json", "r") as f:
            self.config = json.load(f)
        
        self.server_address = (self.config["server"]["address"], self.config["server"]["port"])

app = App()

threading.Thread(target=initializer.init, args=(app,)).start()

if app.config["modules"]["client"]:
    threading.Thread(target=client.init, args=(app,)).start()

app.ready.wait()

threading.Thread(target=server.init, args=(app,)).start()
threading.Thread(target=message_processor.init, args=(app,)).start()

load_modules(app)
# load_plugins(app)