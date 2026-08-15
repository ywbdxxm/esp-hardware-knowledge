import pytest
from docling.datamodel.accelerator_options import AcceleratorDevice

from espdocs.gpu import (
    GpuStatus,
    GpuUnavailableError,
    gpu_status,
    resolve_accelerator_device,
)


def test_cuda_requires_torch_and_onnx_providers(monkeypatch) -> None:
    monkeypatch.setattr(
        "espdocs.gpu.gpu_status",
        lambda: GpuStatus(
            ready=False,
            torch_cuda=True,
            torch_cuda_version="13.0",
            onnx_cuda=False,
            onnx_providers=("CPUExecutionProvider",),
            device_name="Test GPU",
            memory_mib=16384,
        ),
    )

    with pytest.raises(GpuUnavailableError, match="ONNX"):
        resolve_accelerator_device("cuda")


def test_cuda_is_selected_when_both_stacks_are_ready(monkeypatch) -> None:
    monkeypatch.setattr(
        "espdocs.gpu.gpu_status",
        lambda: GpuStatus(
            ready=True,
            torch_cuda=True,
            torch_cuda_version="13.0",
            onnx_cuda=True,
            onnx_providers=("CUDAExecutionProvider", "CPUExecutionProvider"),
            device_name="Test GPU",
            memory_mib=16384,
        ),
    )

    assert resolve_accelerator_device("cuda") is AcceleratorDevice.CUDA


def test_cpu_requires_explicit_selection(monkeypatch) -> None:
    monkeypatch.setattr("espdocs.gpu.torch.cuda.is_available", lambda: False)
    monkeypatch.setattr("espdocs.gpu.ort.get_available_providers", lambda: ["CPUExecutionProvider"])

    assert resolve_accelerator_device("cpu") is AcceleratorDevice.CPU


def test_gpu_status_reports_both_runtime_stacks(monkeypatch) -> None:
    monkeypatch.setattr("espdocs.gpu.torch.cuda.is_available", lambda: True)
    monkeypatch.setattr("espdocs.gpu.torch.cuda.get_device_name", lambda _index: "Test GPU")
    monkeypatch.setattr(
        "espdocs.gpu.torch.cuda.get_device_properties",
        lambda _index: type("Properties", (), {"total_memory": 16 * 1024**3})(),
    )
    monkeypatch.setattr(
        "espdocs.gpu.ort.get_available_providers",
        lambda: ["CUDAExecutionProvider", "CPUExecutionProvider"],
    )

    status = gpu_status()

    assert status.ready is True
    assert status.device_name == "Test GPU"
    assert status.memory_mib == 16384
