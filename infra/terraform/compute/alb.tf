resource "aws_lb" "application" {
  name               = "cricksy-ai-alb"
  load_balancer_type = "application"
  internal           = false
  security_groups    = [var.sg_alb_id]
  subnets            = var.public_subnets

  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "edge"
  }
}

resource "aws_lb_target_group" "api" {
  name        = "cricksy-ai-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = var.vpc_id
  target_type = "ip"

  health_check {
    path                = "/health"
    matcher             = "200-399"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 2
  }

  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "edge"
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.application.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.api.arn
  }

  tags = {
    project = "cricksy-ai"
    env     = "prod"
    tier    = "edge"
  }
}
