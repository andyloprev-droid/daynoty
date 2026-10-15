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
    parser.add_argument("--log", default=None,
                        help="archivo de registro (para correr sin ventana)")
    parser.add_argument("--force", nargs="*", default=[],
                        help="fotos aprobadas a mano (ej. 32.jpg): se procesan "
                             "aunque el filtro las haya descartado")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename=args.log,
        encoding="utf-8",
    )
    log = logging.getLogger("local_photos")
    source = LocalPhotoSource(args.folder)

    while True:
        try:
            stats = source.process_new(force_files=args.force)
            log.info(f"Pasada completa: {stats}")
        except Exception:
            # No dejar que un error (red, API) mate el vigilante
            log.exception("Error en la pasada; se reintenta en la proxima")
            if not args.watch:
                raise
        if not args.watch:
            break
        time.sleep(args.watch * 60)


if __name__ == "__main__":
    main()
