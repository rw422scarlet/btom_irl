#! /bin/bash
python train_rambo_mujoco.py \
--filename "hopper-medium-expert-v2.p" \
--cp_path "none" \
--dynamics_path "../exp/dynamics/03-10-2023 17-31-51" \
--num_samples 100000 \
--norm_obs False \
--norm_rwd False \
--ensemble_dim 7 \
--topk 5 \
--hidden_dim 200 \
--num_hidden 2 \
--activation relu \
--gamma 0.99 \
--beta 1. \
--polyak 0.995 \
--tune_beta True \
--clip_lv True \
--residual False \
--rwd_clip_max 10. \
--obs_penalty 1. \
--adv_penalty 3e-4 \
--norm_advantage True \
--update_critic_adv False \
--buffer_size 1000000 \
--batch_size 256 \
--rollout_batch_size 50000 \
--rollout_min_steps 1 \
--rollout_max_steps 5 \
--rollout_min_epoch 50 \
--rollout_max_epoch 200 \
--model_retain_epochs 4 \
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
--epochs 1000 \
--max_steps 1000 \
--steps_per_epoch 1000 \
--sample_model_every 250 \
--update_model_every 1000 \
--update_policy_every 1 \
--cp_every 10 \
--num_eval_eps 5 \
--eval_deterministic True \
--verbose 50 \
--render False \
--save False \
--seed 0