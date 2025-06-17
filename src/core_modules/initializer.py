from Crypto.PublicKey import ECC

def init(application_object):
    global app
    app = application_object

    if app.config["modules"]["client"]:
        key = app.key.get()
    else:
        key = ECC.generate(curve = "ed25519")

    app.global_private = key

    app.ready.set()