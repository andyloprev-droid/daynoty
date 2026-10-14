"""
Procesa las fotos numeradas de la carpeta local y las sube al dashboard.

Uso:
    python process_local_photos.py                 # una pasada
    python process_local_photos.py --watch 5       # revisar cada 5 minutos
    python process_local_photos.py --folder "C:\\otra\\carpeta"
"""
import argparse
import logging
import time

from processors.local_photo_source import LocalPhotoSource

DEFAULT_FOLDER = r"C:\Users\andyl\Downloads\fotos facebook"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", default=DEFAULT_FOLDER)
    parser.add_argument("--watch", type=float, default=0,
                        help="minutos entre revisiones (0 = una sola pasada)")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    log = logging.getLogger("local_photos")
    source = LocalPhotoSource(args.folder)

    while True:
        stats = source.process_new()
        log.info(f"Pasada completa: {stats}")
        if not args.watch:
            break
        time.sleep(args.watch * 60)


if __name__ == "__main__":
    main()
