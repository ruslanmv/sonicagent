"""Turn a measured endpoint report into Markdown. Numbers come only from the JSON."""

from __future__ import annotations


def _ms(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:.0f}"


def _rtf(value: object) -> str:
    if not isinstance(value, (int, float)):
        return "—"
    return f"{value:.3f}"


def _series_row(series: dict[str, object]) -> str:
    summary = series.get("summary") if isinstance(series.get("summary"), dict) else {}
    total = summary.get("total_ms") if isinstance(summary.get("total_ms"), dict) else {}
    audio = summary.get("audio_ms") if isinstance(summary.get("audio_ms"), dict) else {}
    rtf = summary.get("rtf") if isinstance(summary.get("rtf"), dict) else {}
    warmup = series.get("warmup") if isinstance(series.get("warmup"), dict) else {}
    return (
        f"| {series.get('name')} | {summary.get('n', 0)} | {summary.get('errors', 0)} "
        f"| {_ms(warmup.get('total_ms'))} | {_ms(total.get('p50'))} | {_ms(total.get('p95'))} "
        f"| {_ms(audio.get('p50'))} | {_rtf(rtf.get('p50'))} |"
    )


def render_markdown(report: dict[str, object]) -> str:
    target = report.get("target") if isinstance(report.get("target"), dict) else {}
    client = report.get("client") if isinstance(report.get("client"), dict) else {}
    series = report.get("series") if isinstance(report.get("series"), list) else []
    lines = [
        "# Speech endpoint capability",
        "",
        "One measured pass of the HTTP speech API. This is not a production service level, "
        "and it is not a Quest, phone, or glasses test.",
        "",
        f"- Measured at: {report.get('measured_at')}",
        f"- Target: {target.get('base_url')}",
        f"- Space stage: {target.get('space_stage')} · hardware: {target.get('space_hardware')} "
        f"· region: {target.get('space_region')} · runtime sha: {target.get('space_sha')}",
        f"- Git commit recorded by the probe: {target.get('git_commit')} · dirty: {target.get('git_dirty')}",
        f"- Client: {client.get('platform')} · Python {client.get('python')} · CPUs {client.get('cpu_count')}",
        f"- Authentication: {report.get('auth')}",
        "",
        "The client is a Linux VM calling Hugging Face over HTTPS. A headset on another network "
        "would add its own radio and geographic delay. Time to first audio is the time until the "
        "entire WAV (or JSON transcript) has arrived. The API does not stream partial audio.",
        "",
        "| Series | Samples | Errors | Warmup ms | Total p50 ms | Total p95 ms | Audio p50 ms | RTF p50 |",
        "| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in series:
        if isinstance(item, dict):
            lines.append(_series_row(item))
    lines.extend(
        [
            "",
            "Warmup is the first call and is not included in the percentiles. A cold voice can spend "
            "that call loading its model. RTF is client-observed seconds divided by audio seconds. "
            "Below 1 means the full clip came back faster than its own duration. The listener still "
            "waits for that full clip before playback can start.",
            "",
            "## VR, AR, and mobile",
            "",
            "A conversational headset needs the first sound soon after the person stops speaking. "
            "This deployment answers with one batch request: record, upload, wait, then play. "
            "`/health/ready` reports realtime speech as not implemented, so barge-in and "
            "phrase-by-phrase playback are not available on this path.",
            "",
            "Preset example WAVs are a different path. They are static files. A client can start "
            "those lines after a download, without Piper. Generated lines cannot.",
            "",
            "CPU Basic is a shared cloud CPU. It can sleep. It is not an on-device mobile runtime "
            "and it is not a GPU speech cluster. Use these figures to size the next engine. "
            "Do not quote them as the latency of a VR product.",
            "",
        ]
    )
    heard = [item for item in series if isinstance(item, dict) and item.get("transcript")]
    if heard:
        lines.extend(["## Recognition", ""])
        for item in heard:
            lines.append(f"- {item.get('name')}: {item.get('transcript')}")
        lines.append("")
    notes = report.get("notes")
    if isinstance(notes, list) and notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")
        lines.append("")
    return "\n".join(lines)
