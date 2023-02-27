#! /bin/bash
python train_rambo_mujoco.py \
--filename "hopper-medium-expert-v2.p" \
--cp_path "none" \
--dynamics_path "../exp/dynamics/02-21-2023 22-25-32" \
--num_samples 100000 \
--norm_obs True \
--norm_rwd False \
--ensemble_dim 7 \
--hidden_dim 128 \
--num_hidden 2 \
--activation relu \
--gamma 0.99 \
--beta 0.2 \
--polyak 0.995 \
--tune_beta True \
--clip_lv True \
--rwd_clip_max 5. \
--obs_penalty 3e-4 \
--buffer_size 1000000 \
--batch_size 200 \
--rollout_batch_size 50000 \
--rollout_steps 5 \
--topk 5 \
--rollout_min_epoch 50 \
--rollout_max_epoch 200 \
--real_ratio 0.5 \
--eval_ratio 0.2 \
--m_steps 1000 \
--a_steps 1 \
--lr_a 1e-4 \
--lr_c 3e-4 \
--lr_m 3e-4 \
--decay "0.000025, 0.00005, 0.000075, 0.0001" \
--grad_clip 100. \
--env_name "Hopper-v4" \
--pretrain_steps 0 \
--epochs 2000 \
--max_steps 1000 \
--steps_per_epoch 1000 \
--sample_model_every 250 \
--update_policy_every 1 \
--cp_every 10 \
--num_eval_eps 5 \
--verbose 50 \
--render False \
--save False \
--seed 0