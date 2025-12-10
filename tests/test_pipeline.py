"""
Pipeline tests
"""
import pytest


class TestPipeline:
    """Test ETL pipeline components"""
    
    def test_data_source_config(self):
        """Test data source configuration is valid"""
        import yaml
        
        with open("configs/data-sources.yml", 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'sources' in config
        assert len(config['sources']) > 0
        
        for source in config['sources']:
            assert 'name' in source
            assert 'type' in source
            assert 'path' in source
            assert 'schema' in source
    
    def test_cluster_config(self):
        """Test cluster configuration is valid"""
        import yaml
        
        with open("configs/cluster-configurations.yml", 'r') as f:
            config = yaml.safe_load(f)
        
        for env in ['dev', 'staging', 'prod']:
            assert env in config
            assert 'node_type_id' in config[env]
            assert 'num_workers' in config[env]
    
    def test_monitoring_config(self):
        """Test monitoring configuration is valid"""
        import yaml
        
        with open("configs/monitoring-config.yml", 'r') as f:
            config = yaml.safe_load(f)
        
        assert 'alerts' in config
        assert 'notification_channels' in config


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
