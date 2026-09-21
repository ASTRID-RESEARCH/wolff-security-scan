import argparse
import os
import sys
import time

from scanner.gan.train import train_gan
from scanner.gan.generate import load_trained_generator, generate_payloads_for_endpoint
from scanner.swagger_parser import load_swagger, get_base_url, extract_endpoints, print_endpoints_summary
from scanner.attacker import attack_endpoint
from scanner.analyzer import classify_result, compute_metrics
from scanner.report import generate_report, print_report_summary


def cmd_train(args):
    """Comando para treinar a GAN."""
    config = {}
    if args.epochs:
        config["epochs"] = args.epochs
    if args.batch_size:
        config["batch_size"] = args.batch_size
    config["train_ratio"] = args.train_ratio
    config["val_ratio"] = args.val_ratio
    config["test_ratio"] = args.test_ratio
    config["split_seed"] = args.split_seed
    config["validation_max_batches"] = args.validation_max_batches
    config["test_max_batches"] = args.test_max_batches

    train_gan(
        datasets_dir=args.datasets_dir,
        output_dir=args.output_dir,
        config=config,
        resume_path=args.resume,
    )


def cmd_scan(args):
    """Comando para executar o scan de vulnerabilidades."""
    start_time = time.time()

    # 1. Carregar modelo GAN treinado
    print("Carregando modelo GAN treinado...")
    generator, vocab, config = load_trained_generator(args.model_path)

    # 2. Parsear Swagger — mapear rotas, métodos e parâmetros da API
    swagger = load_swagger(args.swagger)
    base_url = args.base_url or get_base_url(swagger)
    endpoints = extract_endpoints(swagger)
    print_endpoints_summary(endpoints)

    # 3. Para cada endpoint, gerar payloads contextualizados e atacar
    all_results = []
    for ep in endpoints:
        if not ep["params"]:
            continue

        # GAN gera ataques direcionados ao endpoint com base no Swagger
        payloads = generate_payloads_for_endpoint(
            generator, vocab, config,
            endpoint=ep,
            num_payloads=args.num_payloads,
            base_temperature=args.temperature,
        )

        print(f"\n[Atacando] {ep['method']} {ep['path']} ({len(payloads)} payloads gerados pela GAN)...")
        results = attack_endpoint(base_url, ep, payloads, auth_token=args.auth_token)

        # Classificar resultados
        for r in results:
            r["classification"] = classify_result(r)
            all_results.append(r)

    # 4. Computar métricas
    classifications = [r["classification"] for r in all_results]
    metrics = compute_metrics(classifications)

    # Adicionar tempo de execução
    total_time = time.time() - start_time
    metrics["execution_time_seconds"] = round(total_time, 2)

    # 5. Gerar relatório
    report = generate_report(all_results, metrics, output_path=args.output)
    print_report_summary(report)

    print(f"\nTempo total de execução: {total_time:.2f}s")
    print(f"Relatório salvo em: {args.output}")

    # Outputs do Github
    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"vulnerable={'true' if report['vulnerabilities'] else 'false'}\n")
            f.write(f"total-attacks={metrics['total_attacks']}\n")
            f.write(f"true-positives={metrics['true_positives']}\n")
            f.write(f"precision={metrics['precision']}\n")
            f.write(f"efficacy={metrics['efficacy']}\n")
            f.write(f"execution-time={metrics['execution_time_seconds']}\n")
            f.write(f"report-path={args.output}\n")

    # Retornar código de saída baseado em vulnerabilidades
    if report["vulnerabilities"]:
        sys.exit(1)  # Falha no pipeline se houver vulnerabilidades


def main():
    parser = argparse.ArgumentParser(
        # Agradecimentos pela minha esposa por ter sugerido o nome da ferramenta
        description="Wolff Security Scan GAN - Scan de vulnerabilidades de Injeção SQL Baseada em GANs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponíveis")

    # Comando: train
    train_parser = subparsers.add_parser("train", help="Treinar o modelo GAN")
    train_parser.add_argument("--datasets-dir", default="datasets", help="Diretório dos datasets")
    train_parser.add_argument("--output-dir", default="models", help="Diretório para salvar o modelo")
    train_parser.add_argument("--epochs", type=int, default=None, help="Número de épocas")
    train_parser.add_argument("--batch-size", type=int, default=None, help="Tamanho do batch")
    train_parser.add_argument("--resume", default=None, help="Caminho do checkpoint para continuar treino")
    train_parser.add_argument("--train-ratio", type=float, default=0.7, help="Proporção do conjunto de treino")
    train_parser.add_argument("--val-ratio", type=float, default=0.15, help="Proporção do conjunto de validação")
    train_parser.add_argument("--test-ratio", type=float, default=0.15, help="Proporção do conjunto de teste")
    train_parser.add_argument("--split-seed", type=int, default=42, help="Semente aleatória da divisão treino/validação/teste")
    train_parser.add_argument("--validation-max-batches", type=int, default=8, help="Máximo de batches para validar por época")
    train_parser.add_argument("--test-max-batches", type=int, default=None, help="Máximo de batches para avaliar no teste final")

    # Comando: scan
    scan_parser = subparsers.add_parser("scan", help="Executar scan de vulnerabilidades")
    scan_parser.add_argument("--swagger", required=True, help="Caminho do arquivo Swagger YAML/JSON")
    scan_parser.add_argument("--base-url", default=None, help="URL base da API (sobrescreve o Swagger)")
    scan_parser.add_argument("--model-path", default="models/gan_sqli.pt", help="Caminho do modelo treinado")
    scan_parser.add_argument("--num-payloads", type=int, default=200, help="Número de payloads a gerar")
    scan_parser.add_argument("--temperature", type=float, default=0.7, help="Temperatura da geração")
    scan_parser.add_argument("--output", default="reports/scan_report.json", help="Caminho do relatório")
    scan_parser.add_argument("--auth-token", default=None, help="Token de autenticação (ex: 'Token abc123' ou 'Bearer abc123')")

    args = parser.parse_args()

    if args.command == "train":
        cmd_train(args)
    elif args.command == "scan":
        cmd_scan(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
