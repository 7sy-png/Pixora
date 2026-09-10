"""Run an end-to-end check against a live Pixora distributed cluster."""

import argparse
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
from time import monotonic, sleep
from uuid import uuid4

from PIL import Image


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.models import ProcessingOptions
from app.services import DistributedApiError, DistributedClient


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Проверить распределённую обработку Pixora через API"
    )
    parser.add_argument(
        "--api-url",
        default="http://127.0.0.1:8000",
        help="Адрес FastAPI-координатора",
    )
    parser.add_argument(
        "--copies",
        type=int,
        default=8,
        help="Количество тестовых изображений",
    )
    parser.add_argument(
        "--expect-workers",
        type=int,
        default=2,
        help="Минимальное ожидаемое число workers",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30,
        help="Максимальное ожидание пакета в секундах",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=PROJECT_ROOT / "output" / "distributed-smoke",
        help="Каталог для скачанных результатов",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_arguments()
    if args.copies < 1 or args.expect_workers < 1 or args.timeout <= 0:
        raise ValueError("Числовые параметры должны быть больше нуля")

    client = DistributedClient(args.api_url)
    readiness_deadline = monotonic() + args.timeout
    while True:
        try:
            if client.check_health():
                break
        except DistributedApiError:
            if monotonic() >= readiness_deadline:
                raise
        if monotonic() >= readiness_deadline:
            raise RuntimeError("Распределённый API не готов")
        sleep(0.5)

    with TemporaryDirectory(prefix="pixora-distributed-") as temporary:
        source_directory = Path(temporary)
        sources: list[Path] = []
        expected_sizes: list[tuple[int, int]] = []
        source_sizes = ((1280, 720), (900, 900), (800, 1200))
        for index in range(args.copies):
            source = source_directory / f"sample-{index + 1}.png"
            source_size = source_sizes[index % len(source_sizes)]
            color = (
                (47 + index * 29) % 256,
                (71 + index * 43) % 256,
                (131 + index * 17) % 256,
            )
            Image.new("RGB", source_size, color).save(source, format="PNG")
            sources.append(source)
            scale = min(640 / source_size[0], 360 / source_size[1])
            resized = (
                max(1, round(source_size[0] * scale)),
                max(1, round(source_size[1] * scale)),
            )
            expected_sizes.append((resized[1], resized[0]))

        created = client.submit_batch(
            sources,
            ProcessingOptions(
                width=640,
                height=360,
                keep_aspect_ratio=True,
                output_format="WEBP",
                quality=72,
                rotation=90,
                flip_horizontal=True,
            ),
        )
        batch_id = str(created["batch_id"])
        print(f"Пакет {batch_id}: задач {created['total']}")

        deadline = monotonic() + args.timeout
        last_progress = -1
        while True:
            status = client.get_batch_status(batch_id)
            progress = int(status["progress"])
            if progress != last_progress:
                print(
                    f"Прогресс {progress}%: "
                    f"готово {status['completed']}, ошибок {status['failed']}"
                )
                last_progress = progress
            if int(status["completed"]) + int(status["failed"]) == int(
                status["total"]
            ):
                break
            if monotonic() >= deadline:
                raise TimeoutError("Пакет не завершился за отведённое время")
            sleep(0.25)

    if int(status["failed"]):
        raise RuntimeError(f"Ошибок обработки: {status['failed']}")

    workers = {
        str(job["worker"])
        for job in status["jobs"]
        if job["status"] == "SUCCESS" and job.get("worker")
    }
    print(f"Workers ({len(workers)}): {', '.join(sorted(workers))}")
    if len(workers) < args.expect_workers:
        raise RuntimeError(
            f"Ожидалось минимум workers: {args.expect_workers}, получено: {len(workers)}"
        )

    output_directory = args.output_dir / f"run-{uuid4().hex[:8]}"
    output_directory.mkdir(parents=True)
    saved: list[Path] = []
    for index, job in enumerate(status["jobs"], start=1):
        if job["status"] != "SUCCESS":
            continue
        output = job["output"]
        destination = output_directory / f"{index:02d}-{output['filename']}"
        saved.append(client.download_result(str(job["job_id"]), destination))

    for saved_path, expected_size in zip(saved, expected_sizes, strict=True):
        with Image.open(saved_path) as result_image:
            if result_image.format != "WEBP" or result_image.size != expected_size:
                raise RuntimeError(
                    "Полученный файл не сохранил исходные пропорции"
                )
    print(f"Скачано результатов: {len(saved)} в {output_directory}")
    print("Распределённый smoke-тест успешно завершён")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
