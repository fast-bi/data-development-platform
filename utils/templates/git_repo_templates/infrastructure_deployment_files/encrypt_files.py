#!/usr/bin/env python3

import os
import sys
import logging
from cryptography.fernet import Fernet, InvalidToken
from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

# Configure rich console
console = Console()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True, console=console)]
)
logger = logging.getLogger("encrypt_files")

def setup_logging(verbose: bool = False) -> None:
    """Configure logging level based on verbosity"""
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)

def get_files_to_process(root_dir: str = ".") -> list[str]:
    files = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Remove hidden directories except .terraform so we still process terraform state files
        dirnames[:] = [d for d in dirnames if (not d.startswith('.')) or d == '.terraform']
        for filename in filenames:
            if filename.startswith("."):
                continue
            if filename in ("encrypt_files.py", "decrypt_files.py", "README.md"):
                continue
            files.append(os.path.join(dirpath, filename))
    return files

def is_fernet_encrypted(data: bytes) -> bool:
    """Check if data appears to be Fernet encrypted"""
    try:
        # Fernet tokens are base64-encoded and have a specific structure
        import base64
        
        # First, check if it looks like base64 (contains only valid base64 chars)
        if not all(c in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in data):
            return False
        
        # Try to decode as base64
        try:
            decoded = base64.urlsafe_b64decode(data + b'=' * (4 - len(data) % 4))
        except Exception:
            return False
        
        # Fernet tokens have a minimum size requirement
        # They contain: version(1) + timestamp(8) + IV(16) + ciphertext(min 1) + HMAC(32) = min 58 bytes
        if len(decoded) < 58:
            return False
            
        # Check if it starts with the Fernet version byte (0x80)
        if decoded[0] != 0x80:
            return False
            
        return True
    except Exception:
        return False

def encrypt_files(key: str, root_directory: str = './', verbose: bool = False) -> None:
    """Encrypt files in the given directory using the provided key"""
    setup_logging(verbose)
    
    try:
        # Validate key
        try:
            fernet = Fernet(key.encode('utf-8'))
            # Test the key with a small encryption/decryption
            test_data = b"test"
            encrypted = fernet.encrypt(test_data)
            decrypted = fernet.decrypt(encrypted)
            if decrypted != test_data:
                raise ValueError("Encryption key validation failed")
        except Exception as e:
            logger.error(f"Invalid encryption key: {str(e)}")
            sys.exit(1)
            
        # Get files to process
        files_to_process = get_files_to_process(root_directory)
        
        if not files_to_process:
            logger.warning("No files found to encrypt")
            return
            
        # Display summary
        console.print(Panel.fit(
            "[bold blue]Encryption Summary[/bold blue]\n"
            f"Root Directory: [yellow]{root_directory}[/yellow]\n"
            f"Total Files: [green]{len(files_to_process)}[/green]",
            title="Encryption Process"
        ))
        
        # Process files with progress bar
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("[cyan]Encrypting files...", total=len(files_to_process))
            
            # Track statistics
            total_files = len(files_to_process)
            encrypted_files = 0
            skipped_files = 0
            error_files = 0
            
            for file_path in files_to_process:
                try:
                    progress.update(task, description=f"[cyan]Encrypting {file_path}...")
                    
                    # Check if file exists and is readable
                    if not os.path.exists(file_path):
                        logger.warning(f"File does not exist: {file_path}")
                        skipped_files += 1
                        progress.advance(task)
                        continue
                        
                    if not os.access(file_path, os.R_OK):
                        logger.warning(f"File is not readable: {file_path}")
                        skipped_files += 1
                        progress.advance(task)
                        continue
                    
                    # Check file size
                    file_size = os.path.getsize(file_path)
                    if file_size == 0:
                        logger.warning(f"File is empty: {file_path}")
                        skipped_files += 1
                        progress.advance(task)
                        continue
                    
                    # Read file content
                    with open(file_path, 'rb') as f:
                        file_data = f.read()
                        
                    # Validate content
                    if not file_data:
                        logger.warning(f"File has no content: {file_path}")
                        skipped_files += 1
                        progress.advance(task)
                        continue
                    
                    # Check if file is already encrypted by trying to decrypt it
                    try:
                        # Try to decrypt with the same key - if it works, it's already encrypted
                        fernet.decrypt(file_data)
                        logger.warning(f"File is already encrypted: {file_path}")
                        skipped_files += 1
                        progress.advance(task)
                        continue
                    except InvalidToken:
                        # Not encrypted with this key, proceed with encryption
                        pass
                    except Exception:
                        # Some other error, assume it's not encrypted and proceed
                        pass
                        
                    # Encrypt content
                    encrypted_data = fernet.encrypt(file_data)
                    
                    # Write encrypted content
                    with open(file_path, 'wb') as f:
                        f.write(encrypted_data)
                        
                    encrypted_files += 1
                    logger.debug(f"Successfully encrypted: {file_path}")
                    
                except Exception as e:
                    logger.error(f"[red]Failed to encrypt {file_path}: {str(e)}[/red]")
                    error_files += 1
                    
                progress.advance(task)
                
        # Display detailed results
        console.print(Panel.fit(
            f"[bold green]✓ Encryption completed[/bold green]\n\n"
            f"Total files processed: [blue]{total_files}[/blue]\n"
            f"Successfully encrypted: [green]{encrypted_files}[/green]\n"
            f"Skipped (empty/unreadable/already encrypted): [yellow]{skipped_files}[/yellow]\n"
            f"Errors: [red]{error_files}[/red]",
            title="Process Complete"
        ))
        
    except Exception as e:
        logger.error(f"[red]An error occurred during encryption: {str(e)}[/red]")
        sys.exit(1)

def analyze_files(root_directory: str = './', verbose: bool = False) -> None:
    """Analyze files to see which need encryption"""
    setup_logging(verbose)
    
    try:
        # Get files to process
        files_to_process = get_files_to_process(root_directory)
        
        if not files_to_process:
            logger.warning("No files found to analyze")
            return
            
        # Display summary
        console.print(Panel.fit(
            "[bold blue]File Analysis Summary[/bold blue]\n"
            f"Root Directory: [yellow]{root_directory}[/yellow]\n"
            f"Total Files: [green]{len(files_to_process)}[/green]",
            title="File Analysis"
        ))
        
        # Analyze files
        need_encryption = []
        already_encrypted = []
        error_files = []
        
        for file_path in files_to_process:
            try:
                # Check if file exists and is readable
                if not os.path.exists(file_path):
                    error_files.append((file_path, "File does not exist"))
                    continue
                    
                if not os.access(file_path, os.R_OK):
                    error_files.append((file_path, "File is not readable"))
                    continue
                
                # Check file size
                file_size = os.path.getsize(file_path)
                if file_size == 0:
                    error_files.append((file_path, "Empty file"))
                    continue
                
                # Read file content
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                    
                # Check if already encrypted
                if len(file_data) > 100 and all(c in b'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in file_data):
                    already_encrypted.append((file_path, f"{file_size} bytes (likely encrypted)"))
                else:
                    need_encryption.append((file_path, f"{file_size} bytes"))
                    
            except Exception as e:
                error_files.append((file_path, str(e)))
        
        # Display results
        console.print(Panel.fit(
            f"[bold green]✓ Analysis completed[/bold green]\n\n"
            f"Total files: [blue]{len(files_to_process)}[/blue]\n"
            f"Need encryption: [yellow]{len(need_encryption)}[/yellow]\n"
            f"Likely already encrypted: [green]{len(already_encrypted)}[/green]\n"
            f"Error files: [red]{len(error_files)}[/red]",
            title="Analysis Results"
        ))
        
        # Show files that need encryption
        if need_encryption:
            console.print("\n[bold yellow]Files That Need Encryption:[/bold yellow]")
            for file_path, info in need_encryption:
                console.print(f"  [yellow]○[/yellow] {file_path} ({info})")
        
        # Show already encrypted files
        if already_encrypted:
            console.print("\n[bold green]Likely Already Encrypted Files:[/bold green]")
            for file_path, info in already_encrypted:
                console.print(f"  [green]✓[/green] {file_path} ({info})")
        
        # Show error files
        if error_files:
            console.print("\n[bold red]Error Files:[/bold red]")
            for file_path, error in error_files:
                console.print(f"  [red]✗[/red] {file_path} - {error}")
        
    except Exception as e:
        logger.error(f"[red]An error occurred during analysis: {str(e)}[/red]")
        sys.exit(1)

def display_help() -> None:
    """Display help information"""
    console.print(Panel.fit(
        "[bold blue]File Encryption Tool[/bold blue]\n\n"
        "Usage:\n"
        "  python encrypt_files.py <encryption_key> [options]\n\n"
        "Options:\n"
        "  -v, --verbose    Enable verbose logging\n"
        "  --check-only     Analyze files without encrypting them\n"
        "  -h, --help       Show this help message\n\n"
        "Examples:\n"
        "  python encrypt_files.py your_encryption_key -v\n"
        "  python encrypt_files.py your_encryption_key --check-only",
        title="Help"
    ))

def main():
    """Main entry point"""
    if len(sys.argv) < 2 or sys.argv[1] in ['-h', '--help']:
        display_help()
        sys.exit(0)
        
    key = sys.argv[1]
    verbose = '-v' in sys.argv or '--verbose' in sys.argv
    check_only = '--check-only' in sys.argv
    
    try:
        if check_only:
            analyze_files(verbose=verbose)
        else:
            encrypt_files(key, verbose=verbose)
    except KeyboardInterrupt:
        console.print("\n[yellow]Process interrupted by user[/yellow]")
        sys.exit(1)

if __name__ == "__main__":
    main()