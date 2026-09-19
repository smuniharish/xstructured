from hypothesis import settings

settings.register_profile("xstructured", deadline=None, max_examples=100)
settings.load_profile("xstructured")
