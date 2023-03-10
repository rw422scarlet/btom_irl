#! /bin/bash
python train_wail_mujoco.py \
--cp_path "none" \
--hidden_dim 128 \
--num_hidden 2 \
--activation relu \
--gamma 0.99 \
--beta 0.2 \
--polyak 0.995 \
--tune_beta False \
--rwd_clip_max 10. \
--buffer_size 1000000 \
--batch_size 256 \
--real_ratio 0.5 \
--d_steps 30 \
--a_steps 50 \
--lr_d 0.0003 \
--lr_a 0.0003 \
--lr_c 0.0003 \
--decay 1e-5 \
--grad_clip 100. \
--grad_penalty 1. \
--grad_target 0. \
--env_name "Hopper-v4" \
--epochs 1000 \
--max_steps 1000 \
--steps_per_epoch 1000 \
--update_after 2000 \
--update_every 50 \
--cp_every 10 \
--eval_steps 1000 \
--num_eval_eps 5 \
--eval_deterministic True \
--verbose 50 \
--render False \
--save False \
--seed 0