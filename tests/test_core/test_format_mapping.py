# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.

"""
Unit tests for format mapping in export/import functionality
"""

import pytest
from fabric_cli.core.fab_types import ItemType, definition_format_mapping


class TestFormatMapping:
    """Test the definition_format_mapping for various item types"""

    def test_spark_job_definition_formats(self):
        """Test SparkJobDefinition format mapping"""
        formats = definition_format_mapping.get(ItemType.SPARK_JOB_DEFINITION, {})
        
        # Check all expected formats exist
        assert "default" in formats
        assert "SparkJobDefinitionV1" in formats
        assert "SparkJobDefinitionV2" in formats
        
        # Check format values
        assert formats["default"] == "?format=SparkJobDefinitionV1"
        assert formats["SparkJobDefinitionV1"] == "?format=SparkJobDefinitionV1"
        assert formats["SparkJobDefinitionV2"] == "?format=SparkJobDefinitionV2"

    def test_semantic_model_formats(self):
        """Test SemanticModel format mapping"""
        formats = definition_format_mapping.get(ItemType.SEMANTIC_MODEL, {})
        
        # Check all expected formats exist
        assert "default" in formats
        assert "TMDL" in formats
        assert "TMSL" in formats
        
        # Check format values
        assert formats["default"] == "?format=TMDL"
        assert formats["TMDL"] == "?format=TMDL"
        assert formats["TMSL"] == "?format=TMSL"

    def test_notebook_formats(self):
        """Test Notebook format mapping"""
        formats = definition_format_mapping.get(ItemType.NOTEBOOK, {})
        
        # Check all expected formats exist
        assert "default" in formats
        assert ".py" in formats
        assert ".ipynb" in formats
        assert "ipynb" in formats
        assert "fabricGitSource" in formats
        
        # Check format values
        assert formats["default"] == "?format=ipynb"
        assert formats[".py"] == "?format=fabricGitSource"
        assert formats[".ipynb"] == "?format=ipynb"
        assert formats["ipynb"] == "?format=ipynb"
        assert formats["fabricGitSource"] == "?format=fabricGitSource"

    def test_unsupported_item_type_has_no_formats(self):
        """Test that unsupported item types have no format mapping"""
        # Report doesn't have format support
        formats = definition_format_mapping.get(ItemType.REPORT, {})
        assert formats == {}

    def test_all_formats_have_query_string_prefix(self):
        """Test that all format values start with ?format="""
        for item_type, formats in definition_format_mapping.items():
            for format_key, format_value in formats.items():
                if format_key != "default":  # Also check default
                    assert format_value.startswith("?format="), \
                        f"Format value '{format_value}' for {item_type}.{format_key} should start with '?format='"
