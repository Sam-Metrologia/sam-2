import os
import re

templates_dir = r'C:\Users\LENOVO\OneDrive\Escritorio\sam-2\core\templates'
files_changed = []

# Patrones a reemplazar
patterns = [
    (r'\|date:"d M Y"', '|date:"Y-m-d"'),
    (r'\|date:"d/m/Y"', '|date:"Y-m-d"'),
    (r"\|date:'d M Y'", '|date:"Y-m-d"'),
    (r"\|date:'d/m/Y'", '|date:"Y-m-d"'),
]

for root, dirs, files in os.walk(templates_dir):
    for filename in files:
        if filename.endswith('.html'):
            filepath = os.path.join(root, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()

                original_content = content
                for old_pattern, new_pattern in patterns:
                    content = re.sub(old_pattern, new_pattern, content)

                if content != original_content:
                    with open(filepath, 'w', encoding='utf-8') as f:
                        f.write(content)
                    files_changed.append(filename)
                    print(f'Modificado: {filename}')
            except Exception as e:
                print(f'Error en {filename}: {e}')

print(f'\nTotal archivos modificados: {len(files_changed)}')
print('Archivos:', ', '.join(files_changed))
