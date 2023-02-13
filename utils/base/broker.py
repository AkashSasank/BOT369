from abc import ABC


class Broker(ABC):
    """
    Base class for writing interfaces for different brokers
    """
    def connect(self):
        """
        Implement login mechanism for broker to get credentials
        :return:
        """

    def validate(self):
        """
        Validate existing credentials
        :return:
        """