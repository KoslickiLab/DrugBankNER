import hashlib
import logging
from pathlib import Path

import paramiko
from tqdm import tqdm


def sftp_expanduser(sftp: paramiko.SFTPClient, path: str) -> str:
    """
    Expand leading ~ using the SFTP user's home directory.
    SFTP often does NOT expand ~ by itself.
    """
    if path == "~":
        return sftp.getcwd() or "."
    if path.startswith("~/"):
        home = sftp.getcwd()  # Usually the home dir right after connect
        if not home:
            home = "."
        return home.rstrip("/") + "/" + path[2:]
    return path


# -----------------------------
# SSH/SFTP + hash verification
# -----------------------------

def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Compute SHA-256 of a local file."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def sh_quote(s: str) -> str:
    """Safe single-argument shell quoting."""
    return "'" + s.replace("'", "'\"'\"'") + "'"


def connect_ssh(
        *,
        host: str,
        username: str,
        port: int,
        key_path: str | None = None,
        password: str | None = None,
        timeout: int = 30,
) -> paramiko.SSHClient:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    kwargs = dict(hostname=host, port=port, username=username, timeout=timeout)
    if key_path:
        kwargs["key_filename"] = key_path
    if password:
        kwargs["password"] = password

    kwargs["allow_agent"] = True
    kwargs["look_for_keys"] = True

    ssh.connect(**kwargs)
    return ssh


def remote_file_exist(
        *,
        host: str,
        username: str,
        port: int,
        remote_path: str,
        key_path: str | None = None,
        password: str | None = None,
) -> bool:
    ssh = connect_ssh(
        host=host,
        username=username,
        port=port,
        key_path=key_path,
        password=password,
    )
    try:
        sftp = ssh.open_sftp()
        try:
            stat = sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        finally:
            sftp.close()
    except Exception:
        return False


def remote_sha256(ssh: paramiko.SSHClient, remote_path: str) -> str:
    """
    Compute SHA-256 of a remote file by running sha256sum (fallback openssl) on server.
    """
    cmd = (
            "bash -lc "
            + sh_quote(
        f"p={remote_path}; p=$(eval echo $p); sha256sum \"$p\" | awk '{{print $1}}'"
    )
    )
    _stdin, stdout, stderr = ssh.exec_command(cmd)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()

    if out:
        return out

    # Fallback if sha256sum isn't installed
    cmd2 = f"bash -lc 'openssl dgst -sha256 {sh_quote(remote_path)} | awk \"{{print \\$NF}}\"'"
    _stdin, stdout, stderr = ssh.exec_command(cmd2)
    out2 = stdout.read().decode("utf-8", errors="replace").strip()
    err2 = stderr.read().decode("utf-8", errors="replace").strip()

    if not out2:
        raise RuntimeError(
            f"Failed to compute remote sha256 for {remote_path}.\n"
            f"sha256sum error: {err}\n"
            f"openssl error: {err2}"
        )
    return out2


def download_sftp_with_progress(
        *,
        ssh: paramiko.SSHClient,
        remote_path: str,
        local_path: Path,
):
    """Download remote_path to local_path via SFTP with a tqdm progress bar."""
    local_path.parent.mkdir(parents=True, exist_ok=True)

    sftp = ssh.open_sftp()
    try:
        remote_path_expanded = sftp_expanduser(sftp, remote_path)

        # (Optional) helpful log
        logging.info(f"Resolved remote path: {remote_path_expanded}")

        total = sftp.stat(remote_path_expanded).st_size

        with tqdm(
                total=total,
                unit="B",
                unit_scale=True,
                unit_divisor=1024,
                desc=local_path.name,
                dynamic_ncols=True,
        ) as pbar:
            last = {"bytes": 0}

            def cb(transferred: int, _total: int):
                delta = transferred - last["bytes"]
                if delta > 0:
                    pbar.update(delta)
                    last["bytes"] = transferred

            sftp.get(remote_path_expanded, str(local_path), callback=cb)
    finally:
        sftp.close()


def ensure_downloaded_and_verified(
        *,
        host: str,
        username: str,
        port: int,
        remote_path: str,
        local_path: Path,
        key_path: str | None = None,
        password: str | None = None,
) -> None:
    """
    If local_path exists and its SHA-256 matches the remote file SHA-256, skip download.
    Otherwise download and verify.
    """
    ssh = connect_ssh(
        host=host,
        username=username,
        port=port,
        key_path=key_path,
        password=password,
    )
    try:
        logging.info(f"Computing remote SHA-256 for: {remote_path}")
        remote_hash = remote_sha256(ssh, remote_path)

        if local_path.exists() and local_path.is_file():
            logging.info(f"Local file exists: {local_path} — computing local SHA-256")
            local_hash = sha256_file(local_path)
            if local_hash.lower() == remote_hash.lower():
                logging.info("✅ Local file already matches remote (hash verified). Skipping download.")
                return
            logging.warning("⚠️ Local file hash mismatch. Re-downloading...")

        logging.info(f"Downloading from {host}:{remote_path} -> {local_path}")
        download_sftp_with_progress(ssh=ssh, remote_path=remote_path, local_path=local_path)

        logging.info("Verifying SHA-256 after download...")
        local_hash = sha256_file(local_path)
        if local_hash.lower() != remote_hash.lower():
            raise RuntimeError(
                "Hash verification failed after download.\n"
                f"Local:  {local_hash}\n"
                f"Remote: {remote_hash}"
            )

        logging.info("✅ Downloaded and verified successfully.")
    finally:
        ssh.close()
