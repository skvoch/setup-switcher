from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "images"
OUTPUT = ROOT / "demo.gif"
ORDER = (
    "panel-desktop.png",
    "panel-driving.png",
    "settings-pc.png",
    "settings-driving.png",
    "settings-hotkeys.png",
)


def main() -> None:
    screenshots = [Image.open(SOURCE / name).convert("RGBA") for name in ORDER]
    width = max(image.width for image in screenshots)
    height = max(image.height for image in screenshots)
    frames = []
    for screenshot in screenshots:
        frame = Image.new("RGBA", (width, height), "#202020")
        position = ((width - screenshot.width) // 2, (height - screenshot.height) // 2)
        frame.alpha_composite(screenshot, position)
        frames.append(frame.convert("RGB"))
    frames[0].save(
        OUTPUT,
        save_all=True,
        append_images=frames[1:],
        duration=700,
        loop=0,
        disposal=2,
    )
    print(f"Created {OUTPUT}")


if __name__ == "__main__":
    main()
