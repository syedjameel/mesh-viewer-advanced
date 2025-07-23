"""
Tests for UI components in the Mesh Viewer application.
"""

import pytest
from unittest.mock import Mock, MagicMock
from ui.components import (
    BaseUIComponent, MenuBarComponent, ControlsPanelComponent,
    InfoPanelComponent, ViewportComponent
)
from ui.managers import UIStateManager, ThemeManager
from core.scene import Scene


class TestBaseUIComponent:
    """Test the base UI component class."""
    
    def test_base_component_initialization(self):
        """Test that base component can be subclassed and initialized."""
        
        class TestComponent(BaseUIComponent):
            def render(self):
                pass
                
        component = TestComponent("test")
        assert component.name == "test"
        assert component.enabled == True
        
    def test_enable_disable_component(self):
        """Test enabling and disabling components."""
        
        class TestComponent(BaseUIComponent):
            def render(self):
                pass
                
        component = TestComponent("test")
        
        component.enabled = False
        assert component.enabled == False
        
        component.enabled = True
        assert component.enabled == True


class TestUIStateManager:
    """Test the UI state manager."""
    
    def test_state_manager_initialization(self):
        """Test state manager initialization."""
        manager = UIStateManager()
        
        assert manager.view_options['wireframe'] == False
        assert manager.view_options['show_axes'] == True
        assert len(manager.loaded_mesh_paths) == 0
        
    def test_view_options_management(self):
        """Test view options management."""
        manager = UIStateManager()
        
        # Test setting wireframe
        manager.set_wireframe(True)
        assert manager.view_options['wireframe'] == True
        
        # Test setting show axes
        manager.set_show_axes(False)
        assert manager.view_options['show_axes'] == False
        
    def test_mesh_path_management(self):
        """Test mesh path management."""
        manager = UIStateManager()
        
        # Add mesh paths
        manager.add_mesh_path("/path/to/mesh1.obj")
        manager.add_mesh_path("/path/to/mesh2.stl")
        
        assert len(manager.loaded_mesh_paths) == 2
        assert "/path/to/mesh1.obj" in manager.loaded_mesh_paths
        
        # Remove mesh path
        manager.remove_mesh_path("/path/to/mesh1.obj")
        assert len(manager.loaded_mesh_paths) == 1
        assert "/path/to/mesh1.obj" not in manager.loaded_mesh_paths
        
        # Clear all paths
        manager.clear_mesh_paths()
        assert len(manager.loaded_mesh_paths) == 0
        
    def test_observer_pattern(self):
        """Test observer pattern for state changes."""
        manager = UIStateManager()
        
        # Mock observer
        observer = Mock()
        manager.register_observer('wireframe', observer)
        
        # Trigger change
        manager.set_wireframe(True)
        
        # Verify observer was called
        observer.assert_called_once()
        args = observer.call_args[0]
        assert args[0] == 'wireframe'  # event type
        assert args[1] == False        # old value
        assert args[2] == True         # new value


class TestThemeManager:
    """Test the theme manager."""
    
    def test_theme_manager_initialization(self):
        """Test theme manager initialization."""
        manager = ThemeManager()
        assert manager.font_title is None
        
    @pytest.mark.skip(reason="Requires ImGui context")
    def test_style_summary(self):
        """Test getting style summary."""
        manager = ThemeManager()
        summary = manager.get_style_summary()
        
        assert isinstance(summary, dict)
        assert 'has_title_font' in summary
        assert 'window_rounding' in summary


class TestMenuBarComponent:
    """Test the menu bar component."""
    
    def test_menu_bar_initialization(self):
        """Test menu bar component initialization."""
        component = MenuBarComponent()
        
        assert component.name == "MenuBar"
        assert component.enabled == True
        
    def test_callback_setting(self):
        """Test setting callbacks."""
        component = MenuBarComponent()
        
        load_callback = Mock()
        clear_callback = Mock()
        reset_callback = Mock()
        
        component.set_callbacks(
            load_callback=load_callback,
            clear_callback=clear_callback,
            reset_view_callback=reset_callback
        )
        
        assert component._load_callback == load_callback
        assert component._clear_callback == clear_callback
        assert component._reset_view_callback == reset_callback
        
    def test_view_options_management(self):
        """Test view options management."""
        component = MenuBarComponent()
        
        options = {'wireframe': True, 'show_axes': False}
        component.set_view_options(options)
        
        assert component.get_view_options() == options


class TestControlsPanelComponent:
    """Test the controls panel component."""
    
    def test_controls_panel_initialization(self):
        """Test controls panel initialization."""
        scene = Mock()
        component = ControlsPanelComponent(scene)
        
        assert component.name == "ControlsPanel"
        assert component.scene == scene
        
    def test_mesh_count_methods(self):
        """Test mesh counting methods."""
        # Create mock scene with mock meshes
        mock_mesh1 = Mock()
        mock_mesh1.selected = True
        mock_mesh1.visible = True
        
        mock_mesh2 = Mock()
        mock_mesh2.selected = False
        mock_mesh2.visible = True
        
        mock_mesh3 = Mock()
        mock_mesh3.selected = True
        mock_mesh3.visible = False
        
        scene = Mock()
        scene.meshes = [mock_mesh1, mock_mesh2, mock_mesh3]
        
        component = ControlsPanelComponent(scene)
        
        assert component.get_selected_mesh_count() == 2  # mesh1 and mesh3
        assert component.get_visible_mesh_count() == 2   # mesh1 and mesh2


class TestInfoPanelComponent:
    """Test the info panel component."""
    
    def test_info_panel_initialization(self):
        """Test info panel initialization."""
        scene = Mock()
        component = InfoPanelComponent(scene)
        
        assert component.name == "InfoPanel"
        assert component.scene == scene
        
    def test_selected_count(self):
        """Test getting selected mesh count."""
        # Create mock scene with mock meshes
        mock_mesh1 = Mock()
        mock_mesh1.selected = True
        
        mock_mesh2 = Mock()
        mock_mesh2.selected = False
        
        scene = Mock()
        scene.meshes = [mock_mesh1, mock_mesh2]
        
        component = InfoPanelComponent(scene)
        
        assert component.get_selected_count() == 1


class TestViewportComponent:
    """Test the viewport component."""
    
    def test_viewport_initialization(self):
        """Test viewport initialization."""
        renderer = Mock()
        camera = Mock()
        input_handler = Mock()
        scene = Mock()
        
        component = ViewportComponent(renderer, camera, input_handler, scene)
        
        assert component.name == "Viewport"
        assert component.renderer == renderer
        assert component.camera == camera
        assert component.input_handler == input_handler
        assert component.scene == scene
        
    def test_viewport_size_property(self):
        """Test viewport size property."""
        renderer = Mock()
        camera = Mock()
        input_handler = Mock()
        scene = Mock()
        
        component = ViewportComponent(renderer, camera, input_handler, scene)
        
        assert component.get_viewport_size() == (800, 600)  # Default size
        
    def test_view_options_setting(self):
        """Test setting view options."""
        renderer = Mock()
        camera = Mock()
        input_handler = Mock()
        scene = Mock()
        
        component = ViewportComponent(renderer, camera, input_handler, scene)
        
        options = {'wireframe': True, 'show_axes': False}
        component.set_view_options(options)
        
        assert component._view_options == options
        
    def test_delete_callback_setting(self):
        """Test setting delete callback."""
        renderer = Mock()
        camera = Mock()
        input_handler = Mock()
        scene = Mock()
        
        component = ViewportComponent(renderer, camera, input_handler, scene)
        
        delete_callback = Mock()
        component.set_delete_callback(delete_callback)
        
        assert component._delete_callback == delete_callback