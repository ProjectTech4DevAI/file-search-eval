import time
import os
import fnmatch
from pathlib import Path
from argparse import ArgumentParser
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from abc import ABC, abstractmethod
from dotenv import load_dotenv

from marker.converters.pdf import PdfConverter
from marker.models import create_model_dict
from marker.output import text_from_rendered

from pyzerox import zerox
import asyncio

from mylib import Logger


@dataclass
class File:
    abs_path: Path
    name: str
    output_dir: Path
    relative_path: Path


class PDFToMarkdown(ABC):
    @abstractmethod
    def process_file_and_save(self, file: File) -> str:
        raise NotImplementedError()


class MarkerPDFToMarkdown(PDFToMarkdown):
    _name = "marker"

    @classmethod
    def process_file_and_save(cls, file: File) -> None:
        output_dir = Path(file.output_dir) / cls._name / file.relative_path
        if os.path.exists(output_dir) is False:
            os.makedirs(output_dir)

        converter = PdfConverter(
            artifact_dict=create_model_dict(),
        )
        rendered = converter(str(file.abs_path))
        text, _, images = text_from_rendered(rendered)

        markdown_file_name = f"{file.abs_path.stem}.md"

        # save text to md file
        with open(output_dir / markdown_file_name, "w") as f:
            f.write(text)


# class XeroxPDFToMarkdown(PDFToMarkdown):
#     _name = "xerox-openai"
#     model = os.environ.get("XEROX_MODEL", "gpt-4o")
#     openai_api_key = os.environ.get("OPENAI_API_KEY", None)
#     custom_system_prompt = None
#     select_pages = None

#     @classmethod
#     def process_file_and_save(cls, file: File) -> None:
#         output_dir = Path(file.output_dir) / cls._name / file.relative_path
#         if os.path.exists(output_dir) is False:
#             os.makedirs(output_dir)

#         async def run_xerox():
#             await zerox(
#                 file_path=str(file.abs_path),
#                 model=cls.model,
#                 output_dir=str(output_dir),
#                 custom_system_prompt=cls.custom_system_prompt,
#                 select_pages=cls.select_pages,
#             )

#         try:
#             asyncio.run(run_xerox())
#         except Exception as e:
#             Logger.error(f"Error processing file {file.abs_path} : {e}")
#             return str(file.abs_path)

#         Logger.info(f"Processed and save file to {file.output_dir}")


if __name__ == "__main__":
    load_dotenv()
    arguments = ArgumentParser()
    arguments.add_argument("--knowledge-root", type=Path)
    arguments.add_argument(
        "--output-dir", type=Path, default=Path(os.getcwd()) / "output"
    )
    args = arguments.parse_args()
    output_dir = args.output_dir

    Logger.info(f"Knowledge base directory : {args.knowledge_root}")

    files_to_process: list[File] = list()
    for root, dirs, files in os.walk(args.knowledge_root):
        for filename in fnmatch.filter(files, "*.pdf"):

            files_to_process.append(
                File(
                    abs_path=Path(root) / filename,
                    name=filename,
                    output_dir=Path(output_dir),
                    relative_path=Path(root).relative_to(args.knowledge_root),
                ),
            )
            print(files_to_process[-1].output_dir)

    Logger.info(f"Files to process : {len(files_to_process)}")

    # Process file and generate markdown
    for pdf_to_md_converter in PDFToMarkdown.__subclasses__():
        converter = pdf_to_md_converter()
        with ThreadPoolExecutor(max_workers=1) as executor:
            futures = [
                executor.submit(converter.process_file_and_save, file)
                for file in files_to_process
            ]
            for future in as_completed(futures):
                res = future.result()

                Logger.info(f"Processed {res}")
