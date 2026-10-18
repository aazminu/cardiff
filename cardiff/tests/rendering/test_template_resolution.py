from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import shutil

import pytest

from cardiff.contract import load_and_validate_request
from cardiff.contract.errors import ValidationOutcome
from cardiff.contract.models import TemplateSelection
from cardiff.rendering import (
    DeterministicTeXAdapter,
    RenderFailureClass,
    RenderStatus,
    get_default_template_root,
    render_request_to_pdf,
    resolve_template,
)
from cardiff.rendering.tex import BaseTeXAdapter, TeXCompileArtifact

FIXTURES_ROOT = Path(__file__).resolve().parents[1] / "fixtures"
APPROVED_ASSETS = FIXTURES_ROOT / "approved-assets"
APPROVED_SAMPLES = FIXTURES_ROOT / "approved-samples" / "business-card"
REQUEST_PATH = FIXTURES_ROOT / "requests" / "valid-request.yaml"


def _load_request():
    result = load_and_validate_request(
        REQUEST_PATH,
        approved_asset_roots=(APPROVED_ASSETS,),
    )
    assert result.outcome == ValidationOutcome.ACCEPTED
    assert result.request is not None
    return result.request


def test_approved_business_card_template_resolves():
    request = _load_request()

    resolved = resolve_template(request.template)

    assert resolved.descriptor.template_id == "business-card"
    assert resolved.descriptor.page_width_pt == 252.0
    assert resolved.descriptor.page_height_pt == 144.0
    assert resolved.entrypoint_path.name == "card.tex"


def test_missing_template_is_classified_before_compilation():
    request = _load_request()
    missing_request = replace(
        request,
        template=TemplateSelection(
            template_id="missing-card",
            options=dict(request.template.options),
        ),
    )

    result = render_request_to_pdf(
        missing_request,
        APPROVED_SAMPLES / "missing-template.pdf",
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=DeterministicTeXAdapter(),
    )

    assert result.status == RenderStatus.FAILED
    assert result.failure_class == RenderFailureClass.TEMPLATE_NOT_FOUND


class RecordingAdapter(BaseTeXAdapter):
    runtime_name = "recording-adapter"
    runtime_version = "1"
    deterministic = True

    def __init__(self) -> None:
        self.compile_calls = 0
        self._delegate = DeterministicTeXAdapter()

    def compile(
        self,
        tex_source: str,
        output_path: str | Path,
        *,
        page_size_pt: tuple[float, float],
        preview_lines: tuple[str, ...],
        title: str,
    ) -> TeXCompileArtifact:
        self.compile_calls += 1
        return self._delegate.compile(
            tex_source,
            output_path,
            page_size_pt=page_size_pt,
            preview_lines=preview_lines,
            title=title,
        )


def _copy_template_with_manifest(tmp_path: Path, **manifest_updates) -> Path:
    template_root = tmp_path / "templates"
    template_dir = template_root / "business-card"
    shutil.copytree(get_default_template_root() / "business-card", template_dir)
    manifest_path = template_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for key, value in manifest_updates.items():
        if value is None:
            manifest.pop(key, None)
        else:
            manifest[key] = value
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return template_root


@pytest.mark.parametrize(
    ("required_field", "identity_updates"),
    [
        ("phone", {}),
        ("address_lines", {"address_lines": ()}),
    ],
)
def test_manifest_required_identity_field_is_enforced_before_compilation(
    tmp_path,
    required_field,
    identity_updates,
):
    request = _load_request()
    request = replace(request, identity=replace(request.identity, **identity_updates))
    template_root = _copy_template_with_manifest(
        tmp_path,
        required_identity_fields=["full_name", "role", "email", required_field],
    )
    output_path = tmp_path / "out" / "card.pdf"
    adapter = RecordingAdapter()

    result = render_request_to_pdf(
        request,
        output_path,
        template_root=template_root,
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=adapter,
    )

    assert result.status == RenderStatus.FAILED
    assert result.failure_class == RenderFailureClass.TEMPLATE_FIELD_MISSING
    assert result.to_dict()["failure_class"] == "template_field_missing"
    assert result.output_path is None
    assert adapter.compile_calls == 0
    assert not output_path.exists()
    assert any(f"identity.{required_field}" in message for message in result.diagnostics)


def test_all_missing_manifest_required_identity_fields_are_reported(tmp_path):
    request = _load_request()
    template_root = _copy_template_with_manifest(
        tmp_path,
        required_identity_fields=["full_name", "phone", "website"],
    )

    result = render_request_to_pdf(
        request,
        tmp_path / "card.pdf",
        template_root=template_root,
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=RecordingAdapter(),
    )

    assert result.failure_class == RenderFailureClass.TEMPLATE_FIELD_MISSING
    assert any("identity.phone" in message for message in result.diagnostics)
    assert any("identity.website" in message for message in result.diagnostics)
    assert not any("identity.full_name" in message for message in result.diagnostics)


@pytest.mark.parametrize(
    ("required_field", "identity_updates"),
    [
        ("phone", {"phone": "+1 555 0100"}),
        ("address_lines", {}),
    ],
)
def test_manifest_required_identity_field_present_renders(
    tmp_path,
    required_field,
    identity_updates,
):
    request = _load_request()
    request = replace(request, identity=replace(request.identity, **identity_updates))
    template_root = _copy_template_with_manifest(
        tmp_path,
        required_identity_fields=["full_name", "role", "email", required_field],
    )
    adapter = RecordingAdapter()

    result = render_request_to_pdf(
        request,
        tmp_path / "card.pdf",
        template_root=template_root,
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=adapter,
    )

    assert result.status == RenderStatus.SUCCEEDED
    assert adapter.compile_calls == 1


def test_manifest_without_required_identity_fields_uses_contract_defaults(tmp_path):
    request = _load_request()
    template_root = _copy_template_with_manifest(tmp_path, required_identity_fields=None)

    resolved = resolve_template(request.template, template_root=template_root)
    result = render_request_to_pdf(
        request,
        tmp_path / "card.pdf",
        template_root=template_root,
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=DeterministicTeXAdapter(),
    )

    assert resolved.descriptor.required_identity_fields == ("full_name", "role", "email")
    assert result.status == RenderStatus.SUCCEEDED


def test_manifest_listing_unknown_identity_field_is_invalid(tmp_path):
    request = _load_request()
    template_root = _copy_template_with_manifest(
        tmp_path,
        required_identity_fields=["full_name", "fax"],
    )

    result = render_request_to_pdf(
        request,
        tmp_path / "card.pdf",
        template_root=template_root,
        approved_asset_roots=(APPROVED_ASSETS,),
        tex_adapter=RecordingAdapter(),
    )

    assert result.status == RenderStatus.FAILED
    assert result.failure_class == RenderFailureClass.TEMPLATE_MANIFEST_INVALID
    assert any("'fax'" in message for message in result.diagnostics)
