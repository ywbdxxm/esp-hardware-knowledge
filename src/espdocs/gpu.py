"""Explicit GPU readiness checks for Docling and RapidOCR."""

from __future__ import annotations

import os
from dataclasses import dataclass

import onnxruntime as ort
import torch
from docling.datamodel.accelerator_options import AcceleratorDevice


class GpuUnavailableError(RuntimeError):
    """Raised when CUDA was requested but either runtime would fall back to CPU."""


@dataclass(frozen=True)
class GpuStatus:
    ready: bool
    torch_cuda: bool
    torch_cuda_version: str | None
    onnx_cuda: bool
    onnx_providers: tuple[str, ...]
    device_name: str | None
    memory_mib: int | None


def gpu_status() -> GpuStatus:
    torch_cuda = torch.cuda.is_available()
    providers = tuple(ort.get_available_providers())
    onnx_cuda = "CUDAExecutionProvider" in providers
    device_name = torch.cuda.get_device_name(0) if torch_cuda else None
    memory_mib = None
    if torch_cuda:
        memory_mib = round(torch.cuda.get_device_properties(0).total_memory / 1024**2)
    return GpuStatus(
        ready=torch_cuda and onnx_cuda,
        torch_cuda=torch_cuda,
        torch_cuda_version=torch.version.cuda,
        onnx_cuda=onnx_cuda,
        onnx_providers=providers,
        device_name=device_name,
        memory_mib=memory_mib,
    )


def resolve_accelerator_device(requested: str | None = None) -> AcceleratorDevice:
    selection = (requested or os.environ.get("ESPDOCS_DEVICE", "cuda")).casefold()
    if selection == "cpu":
        return AcceleratorDevice.CPU
    if selection not in {"cuda", "auto"}:
        raise ValueError("ESPDOCS_DEVICE must be 'cuda', 'auto', or 'cpu'")
    status = gpu_status()
    if not status.torch_cuda:
        raise GpuUnavailableError(
            "PyTorch CUDA is unavailable; set ESPDOCS_DEVICE=cpu only for an explicit CPU fallback"
        )
    if not status.onnx_cuda:
        raise GpuUnavailableError(
            "ONNX CUDAExecutionProvider is unavailable; RapidOCR would silently use CPU"
        )
    return AcceleratorDevice.CUDA
