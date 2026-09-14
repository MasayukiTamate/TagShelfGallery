from PIL import Image
from GazoToolsLogic import GazoPicture


def test_drawing_creates_photoimage_after_toplevel(tmp_path):
    class FakeRoot:
        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

    picture = GazoPicture.__new__(GazoPicture)
    picture.parent = FakeRoot()
    picture.StartFolder = "/tmp"
    picture.random_pos = type("DummyVar", (), {"get": lambda self: False})()
    picture.random_size = type("DummyVar", (), {"get": lambda self: False})()
    picture.open_windows = {}
    picture.folder_win = None
    picture.file_win = None
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    picture.vectors_cache = {}
    picture._move_callback = None
    picture._refresh_callback = None

    class FakeImage:
        width = 100
        height = 50

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def resize(self, size, method):
            return ("resized", size, method)

    class FakeWin:
        def __init__(self):
            self._tk_image_refs = []
            self._image_hash = None
            self._image_path = None

        def protocol(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

        def attributes(self, *args, **kwargs):
            return False

        def geometry(self, *args, **kwargs):
            return None

        def title(self, *args, **kwargs):
            return None

        def destroy(self):
            pass

        def winfo_exists(self):
            return True

        def winfo_x(self):
            return 10

        def winfo_y(self):
            return 20

        def winfo_width(self):
            return 100

        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

    events = []

    def fake_toplevel(parent):
        events.append("toplevel")
        return FakeWin()

    def fake_photoimage(image=None, **kwargs):
        events.append("photo")
        master = kwargs.get("master")
        if master is not None and hasattr(master, "_tk_image_refs"):
            obj = object()
            master._tk_image_refs.append(obj)
            return obj
        return object()

    import GazoToolsLogic as logic_module
    original_toplevel = logic_module.tk.Toplevel
    original_photoimage = logic_module.ImageTk.PhotoImage
    original_open = logic_module.Image.open
    logic_module.tk.Toplevel = fake_toplevel
    logic_module.ImageTk.PhotoImage = fake_photoimage

    temp_png = tmp_path / "test.png"
    Image.new("RGB", (10, 10), color="white").save(temp_png)
    logic_module.Image.open = lambda *args, **kwargs: FakeImage()

    try:
        picture.Drawing(str(temp_png))
    finally:
        logic_module.tk.Toplevel = original_toplevel
        logic_module.ImageTk.PhotoImage = original_photoimage
        logic_module.Image.open = original_open

    assert events.index("toplevel") < events.index("photo"), events


def test_drawing_keeps_photo_reference_alive_on_window_and_canvas(tmp_path):
    class FakeRoot:
        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

    picture = GazoPicture.__new__(GazoPicture)
    picture.parent = FakeRoot()
    picture.StartFolder = "/tmp"
    picture.random_pos = type("DummyVar", (), {"get": lambda self: False})()
    picture.random_size = type("DummyVar", (), {"get": lambda self: False})()
    picture.open_windows = {}
    picture.folder_win = None
    picture.file_win = None
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    picture.vectors_cache = {}
    picture._move_callback = None
    picture._refresh_callback = None

    class FakeImage:
        width = 100
        height = 50

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def resize(self, size, method):
            return ("resized", size, method)

    class FakeCanvas:
        def __init__(self):
            self.image = None
            self.created = []

        def pack(self, *args, **kwargs):
            pass

        def create_image(self, *args, **kwargs):
            self.created.append(kwargs.get("image"))
            return "img-id"

    class FakeFrame:
        def pack(self, *args, **kwargs):
            pass

    class FakeWin:
        def __init__(self):
            self._tk_image_refs = []
            self._last_photo = None
            self._image_hash = None
            self._image_path = None
            self._destroyed = False

        def protocol(self, *args, **kwargs):
            pass

        def bind(self, *args, **kwargs):
            pass

        def attributes(self, *args, **kwargs):
            return False

        def geometry(self, *args, **kwargs):
            return None

        def title(self, *args, **kwargs):
            return None

        def destroy(self):
            self._destroyed = True

        def winfo_exists(self):
            return True

        def winfo_x(self):
            return 10

        def winfo_y(self):
            return 20

        def winfo_width(self):
            return 100

        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

    tracked = []

    def fake_toplevel(parent):
        win = FakeWin()
        tracked.append(win)
        return win

    def fake_photoimage(image=None, **kwargs):
        master = kwargs.get("master")
        obj = object()
        tracked.append(obj)
        if master is not None and hasattr(master, "_tk_image_refs"):
            master._tk_image_refs.append(obj)
            master._last_photo = obj
        return obj

    import GazoToolsLogic as logic_module
    original_toplevel = logic_module.tk.Toplevel
    original_photoimage = logic_module.ImageTk.PhotoImage
    original_open = logic_module.Image.open
    logic_module.tk.Toplevel = fake_toplevel
    logic_module.ImageTk.PhotoImage = fake_photoimage

    temp_png = tmp_path / "test.png"
    Image.new("RGB", (10, 10), color="white").save(temp_png)
    logic_module.Image.open = lambda *args, **kwargs: FakeImage()

    try:
        picture.Drawing(str(temp_png))
    finally:
        logic_module.tk.Toplevel = original_toplevel
        logic_module.ImageTk.PhotoImage = original_photoimage
        logic_module.Image.open = original_open

    assert tracked[-1] is not None
    assert tracked[0]._last_photo is not None


def test_focus_event_uses_main_module_without_reimport(tmp_path, monkeypatch):
    class FakeRoot:
        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

    picture = GazoPicture.__new__(GazoPicture)
    picture.parent = FakeRoot()
    picture.StartFolder = "/tmp"
    picture.random_pos = type("DummyVar", (), {"get": lambda self: False})()
    picture.random_size = type("DummyVar", (), {"get": lambda self: False})()
    picture.open_windows = {}
    picture.folder_win = None
    picture.file_win = None
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    picture.vectors_cache = {}
    picture._move_callback = None
    picture._refresh_callback = None

    calls = []

    class FakeImage:
        width = 100
        height = 50

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def resize(self, size, method):
            return ("resized", size, method)

    class FakeWidget:
        def __init__(self, *args, **kwargs):
            self._vars = {}
            self.bind_hook = None

        def pack(self, *args, **kwargs):
            return None

        def grid(self, *args, **kwargs):
            return None

        def bind(self, event, callback):
            self.bind_hook = callback

        def config(self, *args, **kwargs):
            return None

        def place_forget(self):
            return None

        def winfo_exists(self):
            return True

    class FakeWin:
        def __init__(self):
            self._tk_image_refs = []
            self._image_hash = "hash-123"
            self._image_path = "/tmp/test.png"
            self.bind_hook = None
            self.attributes_calls = []
            self._titlebar_controls_added = False
            self._titlebar_topmost_btn = None
            self._tag_label = None

        def protocol(self, *args, **kwargs):
            pass

        def bind(self, event, callback):
            self.bind_hook = callback

        def attributes(self, *args, **kwargs):
            self.attributes_calls.append(kwargs)
            return False

        def geometry(self, *args, **kwargs):
            return None

        def title(self, *args, **kwargs):
            return None

        def destroy(self):
            pass

        def winfo_exists(self):
            return True

        def winfo_x(self):
            return 10

        def winfo_y(self):
            return 20

        def winfo_width(self):
            return 100

        def winfo_screenwidth(self):
            return 1200

        def winfo_screenheight(self):
            return 800

        def after(self, *args, **kwargs):
            return None

        def after_cancel(self, *args, **kwargs):
            return None

    class FakeMainModule:
        def update_active_tag_target(self, file_path, image_hash):
            calls.append((file_path, image_hash))

    fake_main = FakeMainModule()
    monkeypatch.setitem(__import__("sys").modules, "__main__", fake_main)
    monkeypatch.setitem(__import__("sys").modules, "GazoToolsApp", None)

    import GazoToolsLogic as logic_module
    original_toplevel = logic_module.tk.Toplevel
    original_photoimage = logic_module.ImageTk.PhotoImage
    original_frame = logic_module.tk.Frame
    original_label = logic_module.tk.Label
    original_button = logic_module.tk.Button
    original_menu = logic_module.tk.Menu
    original_open = logic_module.Image.open
    logic_module.tk.Toplevel = lambda parent: FakeWin()
    logic_module.tk.Frame = lambda *args, **kwargs: FakeWidget()
    logic_module.tk.Label = lambda *args, **kwargs: FakeWidget()
    logic_module.tk.Button = lambda *args, **kwargs: FakeWidget()
    logic_module.tk.Menu = lambda *args, **kwargs: FakeWidget()
    logic_module.ImageTk.PhotoImage = lambda image=None, **kwargs: object()

    temp_png = tmp_path / "test.png"
    Image.new("RGB", (10, 10), color="white").save(temp_png)
    logic_module.Image.open = lambda *args, **kwargs: FakeImage()

    try:
        picture.Drawing(str(temp_png))
    finally:
        logic_module.tk.Toplevel = original_toplevel
        logic_module.ImageTk.PhotoImage = original_photoimage
        logic_module.tk.Frame = original_frame
        logic_module.tk.Label = original_label
        logic_module.tk.Button = original_button
        logic_module.tk.Menu = original_menu
        logic_module.Image.open = original_open

    win = picture.open_windows.get(str(temp_png))
    assert win is not None
    assert win.bind_hook is not None
    win.bind_hook()
    expected_hash = logic_module.calculate_file_hash(str(temp_png))
    assert calls == [(str(temp_png), expected_hash)]


def test_drawing_ignores_none_filename():
    picture = GazoPicture.__new__(GazoPicture)
    picture.parent = None
    picture.StartFolder = "/tmp"
    picture.random_pos = type("DummyVar", (), {"get": lambda self: False})()
    picture.random_size = type("DummyVar", (), {"get": lambda self: False})()
    picture.open_windows = {}
    picture.folder_win = None
    picture.file_win = None
    picture.tag_dict = {}
    picture.rating_dict = {}
    picture.image_rating_map = {}
    picture.vectors_cache = {}
    picture._move_callback = None
    picture._refresh_callback = None

    try:
        picture.Drawing(None)
    except Exception as exc:
        raise AssertionError(f"None filename should be ignored, but raised {exc!r}")
