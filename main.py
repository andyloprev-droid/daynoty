"""
Main - News Agent Entry Point
"""
import logging
import logging.handlers
import argparse
import sys
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from news_agent import NewsAgent
import config

# ============ Configurar Logging ============


def setup_logging():
    """Configure logging to file and console"""

    # Create logs directory if it doesn't exist
    import os
    os.makedirs(config.LOG_FILE.rsplit("/", 1)[0], exist_ok=True)

    # Root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # Logging format
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        config.LOG_FILE, maxBytes=10485760, backupCount=5
    )  # 10MB
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


# ============ Agente ============


def run_agent_once(agent: NewsAgent):
    """Run agent once"""
    logger = logging.getLogger(__name__)
    logger.info("Running agent once...")
    agent.run()


def daily_cleanup_job(agent: NewsAgent):
    """Borrar todas las noticias del dashboard/BD (limpieza diaria 1 AM Miami)"""
    logger = logging.getLogger(__name__)
    try:
        logger.info("=" * 50)
        logger.info("LIMPIEZA DIARIA PROGRAMADA (1 AM Miami)")
        logger.info("=" * 50)
        deleted = agent.database.delete_all_articles()
        logger.info(f"✓ Se borraron {deleted} artículos. Dashboard limpio.")
        logger.info("=" * 50)
    except Exception as e:
        logger.error(f"Error en limpieza diaria programada: {e}", exc_info=True)


def run_agent_scheduled(agent: NewsAgent):
    """Run agent on schedule"""
    logger = logging.getLogger(__name__)

    scheduler = BackgroundScheduler(
        timezone="America/New_York"  # Miami/Florida timezone
    )

    # Schedule execution every X minutes
    job = scheduler.add_job(
        agent.run,
        "interval",
        minutes=config.SCHEDULER_INTERVAL_MINUTES,
        id="news_agent_job",
        name="News Processor",
    )

    # Limpieza diaria a la 1:00 AM hora Miami (America/New_York)
    scheduler.add_job(
        daily_cleanup_job,
        CronTrigger(hour=1, minute=0, timezone="America/New_York"),
        args=[agent],
        id="daily_cleanup_job",
        name="Daily Cleanup 1AM Miami",
    )

    scheduler.start()

    logger.info(
        f"✓ Scheduler started"
    )
    logger.info(
        f"  Frequency: every {config.SCHEDULER_INTERVAL_MINUTES} minutes"
    )
    logger.info(f"  Timezone: America/New_York (Miami)")
    logger.info(f"  Limpieza diaria programada: 01:00 AM hora Miami")

    try:
        logger.info("Press Ctrl+C to stop...")
        # Keep scheduler running
        while True:
            pass
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler stopped")


def get_daily_summary(agent: NewsAgent):
    """Show daily summary"""
    summary = agent.get_daily_summary()
    logger = logging.getLogger(__name__)

    logger.info("=" * 60)
    logger.info("DAILY SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Date: {summary['date']}")
    logger.info(f"Articles processed today: {summary['total_articles_today']}")
    logger.info(f"Total articles in database: {summary['total_articles_all_time']}")
    logger.info(f"Articles by source: {summary['articles_by_source']}")
    logger.info("=" * 60)


# ============ Main ============


def main():
    """Main entry point"""

    # Configure logging
    logger = setup_logging()

    parser = argparse.ArgumentParser(
        description="News Extraction and Processing Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --run-once         # Run once
  python main.py --schedule         # Run scheduled
  python main.py --summary          # Show daily summary
  python main.py --test-mode        # Test mode (detailed logs)
        """,
    )

    parser.add_argument(
        "--run-once",
        action="store_true",
        help="Run agent once",
    )
    parser.add_argument(
        "--schedule",
        action="store_true",
        help="Run agent on schedule (every X minutes)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Show daily news summary",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode (detailed logging)",
    )

    args = parser.parse_args()

    # If no arguments, show help
    if not any([args.run_once, args.schedule, args.summary, args.test_mode]):
        parser.print_help()
        return

    logger.info(f"News Agent started - {datetime.now()}")
    logger.info(f"Environment: {config.ENV}")

    try:
        # Initialize agent
        agent = NewsAgent()

        # Test mode
        if args.test_mode:
            logger.setLevel(logging.DEBUG)
            logger.info("TEST MODE ACTIVATED (DEBUG)")
            args.run_once = True  # Run once in debug mode

        # Run once
        if args.run_once:
            run_agent_once(agent)

        # Run scheduled
        elif args.schedule:
            run_agent_scheduled(agent)

        # Show summary
        elif args.summary:
            get_daily_summary(agent)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
