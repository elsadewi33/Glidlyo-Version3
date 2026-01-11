"""Factory for creating video generation runners."""
from typing import Optional
from generation.base_runner import BaseRunner
from generation.default_runner import DefaultRunner
from generation.flow_runner import FlowRunner
from generation.google_flow_runner import GoogleFlowRunner
from core.models import GenerationConfig
from core.logger import Logger
from core.config import config


def create_runner(gen_config: GenerationConfig, logger: Logger) -> Optional[BaseRunner]:
    """Create appropriate runner based on configuration.
    
    Args:
        gen_config: Generation configuration
        logger: Logger instance
    
    Returns:
        Appropriate runner instance or None if invalid configuration
    """
    subcategory = gen_config.video_gen_subcategory
    gen_method = gen_config.gen_method
    
    # Determine which runner to use
    if subcategory == "Google Flow":
        # Google Flow runner
        if not gen_config.google_flow_username or not gen_config.google_flow_password:
            logger.error("Google Flow credentials not provided")
            return None
        
        return GoogleFlowRunner(
            config=gen_config,
            logger=logger,
            username=gen_config.google_flow_username,
            password=gen_config.google_flow_password,
            timeout=gen_config.timeout
        )
    
    elif gen_method == "Flow" or subcategory == "Flow Video Generator":
        # Flow runner
        return FlowRunner(
            config=gen_config,
            logger=logger,
            email=config.email,
            password=config.pwd,
            ffmpeg_path=config.ffmpeg_path,
            timeout=gen_config.timeout,
            extensions_root=config.flow_extensions_root,
            user_data_dir=config.flow_user_data_dir,
            download_dir="",  # Will be set per JSON file
            headless=config.flow_headless,
            start_account_index=config.flow_account_start,
            preferred_ext_id=config.flow_ext_id
        )
    
    elif subcategory == "Nexa":
        # Nexa runner (like Default but WITHOUT extensions for captcha solving)
        return DefaultRunner(
            config=gen_config,
            logger=logger,
            email=config.email,
            password=config.pwd,
            ffmpeg_path=config.ffmpeg_path,
            timeout=gen_config.timeout,
            use_extensions=False  # No captcha solver extensions
        )
    
    else:
        # Default runner (Playwright Nexabot with extensions)
        return DefaultRunner(
            config=gen_config,
            logger=logger,
            email=config.email,
            password=config.pwd,
            ffmpeg_path=config.ffmpeg_path,
            timeout=gen_config.timeout,
            use_extensions=True  # Use captcha solver extensions
        )
