import os
import socket
import sys
import time
from colorama import Fore, Style
from urllib.parse import urlparse

print(Fore.RED + "----------   GopherThing By TheMangler47 ----------" + Style.RESET_ALL)
print(Fore.RED + "----------   github.com/TheMangler47 ----------" + Style.RESET_ALL)

def get_unique_filename(filepath: str) -> str:
    """If file exists, appends (1), (2), etc. before extension."""
    if not os.path.exists(filepath):
        return filepath
        
    dirname, filename = os.path.split(filepath)
    name, ext = os.path.splitext(filename)
    
    counter = 1
    while True:
        new_filename = f"{name} ({counter}){ext}"
        new_filepath = os.path.join(dirname, new_filename) if dirname else new_filename
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1

def format_file_size(size_in_bytes: int) -> str:
    """Formats raw bytes into readable B, KB, MB, GB."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}" if unit != 'B' else f"{size_in_bytes} Bytes"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def download_file_stream(host: str, port: int, selector: str, output_filepath: str):
    """Streams data straight to disk with clean progress display."""
    chunk_size = 16384  
    downloaded = 0
    last_update = 0
    
    is_idle = 'idlelib' in sys.modules

    with socket.create_connection((host, port)) as client:
        client.sendall(f"{selector}\r\n".encode("utf-8"))
        
        with open(output_filepath, "wb") as f:
            print("\nDownloading...")
            while True:
                chunk = client.recv(chunk_size)
                if not chunk:
                    break
                
                f.write(chunk)
                downloaded += len(chunk)
                
                if is_idle:
                    if downloaded - last_update >= 512 * 1024:
                        blocks = int((downloaded / (512 * 1024)) % 20) + 1
                        bar = "█" * blocks
                        print(f" [{bar:<20}] {format_file_size(downloaded)} downloaded")
                        last_update = downloaded
                else:
                    if time.time() - last_update > 0.1:
                        blocks = int((time.time() * 10) % 20)
                        bar = ["-"] * 20
                        bar[blocks] = "█"
                        sys.stdout.write(f"\rProgress: [{''.join(bar)}] {format_file_size(downloaded)} downloaded")
                        sys.stdout.flush()
                        last_update = time.time()

        if is_idle:
            print(f" [████████████████████] Total: {format_file_size(downloaded)} - Complete!\n")
        else:
            sys.stdout.write(f"\rProgress: [████████████████████] {format_file_size(downloaded)} total! Complete!\n")
            sys.stdout.flush()

    return downloaded

def parse_gopher_menu(menu_bytes: bytearray) -> list:
    """Parses raw text from a Gopher menu into structured items."""
    lines = menu_bytes.decode("utf-8", errors="replace").split("\r\n")
    parsed_items = []

    for line in lines:
        if not line or line == ".":
            continue
        
        item_type = line[0]
        parts = line[1:].split("\t")
        
        parsed_items.append({
            "type": item_type,
            "name": parts[0] if len(parts) > 0 else "",
            "selector": parts[1] if len(parts) > 1 else "",
            "host": parts[2] if len(parts) > 2 else "",
            "port": int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 70
        })
        
    return parsed_items

def parse_gopher_url(url: str):
    """Parses a Gopher URL and strips item type prefixes like 0/, 1/, 7/."""
    if not url.startswith("gopher://"):
        url = f"gopher://{url}"
        
    parsed = urlparse(url)
    host = parsed.hostname
    port = parsed.port or 70
    
    path = parsed.path.lstrip('/')
    item_type = "1"

    if len(path) >= 2 and path[0] in "017" and path[1] == "/":
        item_type = path[0]
        selector = path[2:]
    else:
        selector = path

    if parsed.query:
        selector += f"\t{parsed.query}"

    return host, port, selector, item_type

def get_item_tag(itype: str) -> str:
    tags = {
        "0": "[TXT] ", "1": "[DIR] ", "4": "[HQX] ", "5": "[ZIP] ",
        "6": "[UUE] ", "7": "[SRCH]", "9": "[BIN] ", "g": "[IMG] ",
        "I": "[IMG] ", "s": "[AUDIO]", "d": "[DOC] ", "p": "[PNG] ",
    }
    return tags.get(itype, "[FILE]")

def run_gopher_browser():
    history = []

    initial_url = input("Enter starting Gopher URL (e.g., gopher.floodgap.com): ").strip()
    if not initial_url:
        return

    current_host, current_port, current_selector, _ = parse_gopher_url(initial_url)

    while True:
        try:
            print(f"\nFetching: gopher://{current_host}:{current_port}/1/{current_selector}")
            
            with socket.create_connection((current_host, current_port)) as client:
                client.sendall(f"{current_selector}\r\n".encode("utf-8"))
                raw_data = bytearray()
                while True:
                    b = client.recv(4096)
                    if not b:
                        break
                    raw_data.extend(b)

            items = parse_gopher_menu(raw_data)
            selectable_links = {}

            print("\n" + "=" * 60)
            item_counter = 1
            for item in items:
                itype = item["type"]
                name = item["name"]

                if itype == "i":
                    print(f"       {name}")
                else:
                    tag = get_item_tag(itype)
                    print(f"  {item_counter:2d}. {tag} {name}")
                    selectable_links[item_counter] = item
                    item_counter += 1

            print("=" * 60)
            print("Commands: Type [Number] to open/download, [B]ack, or [Q]uit")
            choice = input("Option > ").strip().lower()

            if choice == "q":
                print("Goodbye!")
                break
            elif choice == "b":
                if history:
                    current_host, current_port, current_selector = history.pop()
                else:
                    print("Already at the root destination.")
            elif choice.isdigit() and int(choice) in selectable_links:
                selected = selectable_links[int(choice)]
                itype = selected["type"]

                if itype == "1":
                    history.append((current_host, current_port, current_selector))
                    current_host = selected["host"] or current_host
                    current_port = selected["port"]
                    current_selector = selected["selector"]

                elif itype == "7":
                    query = input(f"\nEnter search query for {selected['name']}: ").strip()
                    if query:
                        history.append((current_host, current_port, current_selector))
                        current_host = selected["host"] or current_host
                        current_port = selected["port"]
                        current_selector = f"{selected['selector']}\t{query}"
                
                else:
                    raw_filename = os.path.basename(selected["selector"])
                    default_name = raw_filename if raw_filename else "downloaded_file.bin"
                    
                    user_input = input(f"Enter filename to save as [{default_name}]: ").strip()
                    target_name = user_input if user_input else default_name
                    final_filepath = get_unique_filename(target_name)

                    print(f"\nDownloading from {selected['host']}...")
                    try:
                        bytes_written = download_file_stream(
                            selected["host"], 
                            selected["port"], 
                            selected["selector"], 
                            final_filepath
                        )
                        
                        print("=" * 45)
                        print(" [✓] DOWNLOAD COMPLETED")
                        print(f" Saved to : '{final_filepath}'")
                        print(f" Size     : {format_file_size(bytes_written)}")
                        print("=" * 45 + "\n")
                    except Exception as e:
                        print("\n" + "=" * 45)
                        print(" [X] DOWNLOAD FAILED")
                        print(f" Error: {e}")
                        print("=" * 45 + "\n")

            else:
                print("Invalid choice, try again.")

        except Exception as e:
            print(f"Error fetching path: {e}")
            if history:
                print("Returning to previous menu...")
                current_host, current_port, current_selector = history.pop()
            else:
                break

if __name__ == "__main__":
    run_gopher_browser()
