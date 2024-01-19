#!/bin/bash

# Function to replace placeholders in the template
replace_placeholders() {
    template="$1"
    while [[ $template =~ \{([^}]+)\} ]]; do
        placeholder="${BASH_REMATCH[1]}"
        read -p "Enter local path to $placeholder: " value
        template="${template//\{$placeholder\}/$value}"
    done
    echo "$template"
}

# Read the template file
template_file="hydroserver-local-template.yml"
template_content=$(cat "$template_file")

# Replace placeholders
composed_content=$(replace_placeholders "$template_content")

# Save the composed content to a new file (hydroserver-local.yaml)
echo "$composed_content" > hydroserver-local.yaml

echo "Finished setting up Docker Compose file."
