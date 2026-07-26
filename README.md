# SAM ScreenParser
**Note on Naming:** In this project, **SAM** stands for **S**creen **A**utomation **M**anager (and is also a nod to the author's initials, **S**abir **A**li **M**ondal). 
*This project is entirely independent and is NOT related to Meta's Segment Anything Model (SAM).*

## Project Overview

SAM ScreenParser is a local, CPU-friendly screen understanding pipeline designed for desktop automation agents. It converts raw screenshots into structured, deterministic JSON representations containing pixel-perfect coordinates, clean text, element classifications, and window context. The system operates entirely offline, requiring no cloud APIs or dedicated GPU hardware, making it suitable for standard laptops.

## Citation

```bibtex
@software{sam_screenparser_2026,
  title = {SAM ScreenParser: Hybrid Vision Pipeline for Desktop Automation},
  author = {Sabir Ali Mondal},
  year = {2026},
  note = {Florence-2 and Tesseract hybrid for CPU-friendly screen understanding}
}
```

## License & Credits

- Florence-2: Microsoft Research (Apache 2.0 License)
- Tesseract OCR: Google Open Source (Apache 2.0 License)
- OpenCV: OpenCV Team (Apache 2.0 License)
- Transformers: Hugging Face (Apache 2.0 License)
- UIAutomation: Microsoft Windows SDK (Proprietary/Free to use)
