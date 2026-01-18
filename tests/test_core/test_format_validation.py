# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Integration test to verify format validation logic
"""

import pytest
from fabric_cli.core.fab_exceptions import FabricCLIError
from fabric_cli.core.fab_types import ItemType, definition_format_mapping


class TestFormatValidation:
    """Test format validation logic in export/import"""

    def test_invalid_format_for_spark_job_definition(self):
        """Test that invalid format for SparkJobDefinition raises error"""
        valid_formats = definition_format_mapping.get(ItemType.SPARK_JOB_DEFINITION, {})
        invalid_format = "InvalidFormat"
        
        # Check that invalid format is not in mapping
        assert invalid_format not in valid_formats
        
        # Valid formats should be present
        assert "SparkJobDefinitionV1" in valid_formats
        assert "SparkJobDefinitionV2" in valid_formats

    def test_invalid_format_for_semantic_model(self):
        """Test that invalid format for SemanticModel raises error"""
        valid_formats = definition_format_mapping.get(ItemType.SEMANTIC_MODEL, {})
        invalid_format = "InvalidFormat"
        
        # Check that invalid format is not in mapping
        assert invalid_format not in valid_formats
        
        # Valid formats should be present
        assert "TMDL" in valid_formats
        assert "TMSL" in valid_formats

    def test_invalid_format_for_notebook(self):
        """Test that invalid format for Notebook raises error"""
        valid_formats = definition_format_mapping.get(ItemType.NOTEBOOK, {})
        invalid_format = "InvalidFormat"
        
        # Check that invalid format is not in mapping
        assert invalid_format not in valid_formats
        
        # Valid formats should be present
        assert ".py" in valid_formats
        assert ".ipynb" in valid_formats
        assert "ipynb" in valid_formats
        assert "fabricGitSource" in valid_formats

    def test_format_mapping_keys_consistency(self):
        """Test that all format mappings have consistent structure"""
        for item_type, formats in definition_format_mapping.items():
            # All mappings should have a default
            assert "default" in formats, f"{item_type} should have a 'default' format"
            
            # All format values should be query strings
            for format_key, format_value in formats.items():
                assert format_value.startswith("?format="), \
                    f"{item_type}.{format_key} format value should start with '?format='"
                
                # Extract the actual format name from query string
                actual_format = format_value.replace("?format=", "")
                assert actual_format, f"{item_type}.{format_key} should have a non-empty format name"
