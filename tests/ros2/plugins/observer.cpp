// TEST ONLY. This is an observation point, not a navigation controller.
#include <stdexcept>
#include "nav2_core/controller.hpp"
#include "nav2_msgs/msg/speed_limit.hpp"
#include "pluginlib/class_list_macros.hpp"
#include "rclcpp/create_publisher.hpp"

namespace spp_test
{
class BoundaryObserver : public nav2_core::Controller
{
public:
  void configure(
    const rclcpp_lifecycle::LifecycleNode::WeakPtr & parent,
    std::string, std::shared_ptr<tf2_ros::Buffer>,
    std::shared_ptr<nav2_costmap_2d::Costmap2DROS>) override
  {
    auto node = parent.lock();
    if (!node) {throw std::runtime_error("Observer parent expired");}
    // Ordinary diagnostic publisher, independent of navigation activation.
    publisher_ = rclcpp::create_publisher<nav2_msgs::msg::SpeedLimit>(
      node, "spp_boundary_observed", rclcpp::QoS(10).transient_local());
  }
  void cleanup() override {publisher_.reset();}
  void activate() override {}
  void deactivate() override {}
  void setPlan(const nav_msgs::msg::Path &) override
  {throw std::runtime_error("TEST ONLY: path following is not supported");}
  geometry_msgs::msg::TwistStamped computeVelocityCommands(
    const geometry_msgs::msg::PoseStamped &, const geometry_msgs::msg::Twist &,
    nav2_core::GoalChecker *) override
  {throw std::runtime_error("TEST ONLY: motion commands are not supported");}
  void setSpeedLimit(const double & speed_limit, const bool & percentage) override
  {
    nav2_msgs::msg::SpeedLimit observation;
    observation.speed_limit = speed_limit;
    observation.percentage = percentage;
    publisher_->publish(observation);
  }
private:
  rclcpp::Publisher<nav2_msgs::msg::SpeedLimit>::SharedPtr publisher_;
};
}  // namespace spp_test
PLUGINLIB_EXPORT_CLASS(spp_test::BoundaryObserver, nav2_core::Controller)
