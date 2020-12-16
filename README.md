# k53certbot

k53cerbot is specifically targeted at AWS EKS users who want to issue SSL 
certificates based on 
[Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
declarations and are unable to use [cert-manager](https://cert-manager.io/) which is
incompatibility with AWS Fargate.

## Setup
_k53certbot is intented to run as a `deployment` inside the `kube-system` 
namespace of your Kubernetes cluster_

### Container image (requires podman - or build manually with Docker)

The latest image is hosted on 
[quay.io](https://quay.io/repository/declarativesystems/k53certbot) or you can
build yourself:

```shell
make image
```

After building, push the image somewhere you can access it from your EKS
cluster, eg ECR or an Artifactory instance you control.

### Kubernetes RBAC/IAM

1. Create a IAM policy based on the [example](examples/Certbot.iam_policy.json)
    * This grants access to all Route53 resources, you may want to add 
      restrictions
2. Create a Kubernetes service account mapping the [IAM policy to a service
   account in the Kubernetes cluster](https://eksctl.io/usage/iamserviceaccounts/)
    * The example deployment expects service name `certbot-service` 

### Route53

* Configure a
  [public hosted zone](https://docs.aws.amazon.com/Route53/latest/DeveloperGuide/hosted-zones-working-with.html)
  for the zone you wish to issue certificates in

### External DNS

External DNS manages the DNS record _for the ingress_ - follow the instructions
https://github.com/kubernetes-sigs/external-dns/ to setup external-dns

# AWS Load Balancer Controller

AWS Load Balancer Controller exposes the services running behind Ambassador - 
follow the instructions 
https://aws.amazon.com/about-aws/whats-new/2020/10/introducing-aws-load-balancer-controller/
 to setup the load balancer controller

### Ingress controller

* Kubernetes requires an Ingress Controller implementation to make your ingress
  definitions do anything. 
  We suggest [Ambassador](https://www.getambassador.io/products/api-gateway/)

### ZeroSSL Setup (not required if using Letsencrypt)

* Create an 
  [opaque kubernetes secret](https://kubernetes.io/docs/concepts/configuration/secret/) containing the zerossl API key
* The example scripts expect:
    * secret name: `zerossl`
    * data field: `zerossl_api_key`

### k53certbot deployment

Deploy the container image you built to the cluster:

1. Adjust the [example](examples/k53certbot.kubectl.yaml) to suit your environment:
    * `<REPLACE_WITH_YOUR_IMAGE>`
    * `<REPLACE_WITH_YOUR_EMAIL>`
    * remove `--provider zerossl` if using Letsencrypt
2. `kubectl apply -y /path/to/edited/example/k53certbot.kubectl.yaml`
3. Inspect the deployment once its running:
    * `kubectl -n kube-system get pod`
    * `kubectl -n kube-system get deployment ID_OF_DEPLOYMENT`
    * `kubectl -n kube-system logs ID_OF_POD`
    * ...etc

## Provisioning TLS certificates

Once setup is complete, TLS certificates are provisioned by deploying a 
suitable ingress, see [example](examples/ingress.kubectl.yaml) and adjust as
needed, then deploy with:

```shell
kubectl deploy -f /path/to/edited/example/ingress.kubectl.yaml
```

If you've done everything right, the site will start working with TLS in a few
minutes time, otherwise look at the pod logs for the container running 
k53certbot to start working out what is going on.

**Tip**

There are a lot of moving parts needed before k53certbot can work - if you 
manage it all in one go you deserve a medal!

For the rest of us - break your cluster deployment into steps:

1. AWS Load Balancer + ambassador - can you see a service?
2. External-DNS - can you access your deployment over plain `http` with the 
   right hostname?
3. With all this working, your ready to try adding TLS with k53certbot

## How does k53certbot work?

1. Watch Kubernetes for ingress deployments
2. For every change:
    1. Get the FQDN the ingress
    2. run `certbot` to register or de-register the FQDN - certbot has built
       in support for Route 53 via python package `certbot-dns-route53`
    3. `certbot` manages files under `/etc/letsencrypt` and will write the TLS
       secrets there once they have been provisioned.
    4. Create a kubernetes secret including the contents of the appropriate
       files under `/etc/letsencrypt`:
        * Secrets will be named: `tls-<FQDN WITH PERIODS CONVERTED TO HYPHENS>`
          eg: the secret for `example.yourdomain.com` would be 
          `tls-examlple-yourdomain-com` - periods are replaced with hypens as
          they cause problems in Ambassador
        * Any existing secret with the same name will be replaced
       

## Status

* Experimental - does the bare minimum needed to issue an initial certificate


## Features

* [ZeroSSL support](https://zerossl.com/) by adapting 
  [certbot-zerossl](https://github.com/zerossl/certbot-zerossl)
* [Letsencrypt support](https://letsencrypt.org/)
* [DNS-01 challenge support](https://certbot.eff.org/docs/challenges.html#dns-01-challenge)
* [AWS Fargate EKS compatible](https://docs.aws.amazon.com/eks/latest/userguide/fargate.html)
* AWS service access via `iamserviceaccount` - no need (and not supported) to 
  embed AWS access keys in secrets, etc.

## Todo

* Certificate renewal (workaround: restart script)
* Testing, bulletproofing, etc.

## Hacking

**Use live code in docker container**

```shell
rm /usr/local/lib/python3.8/site-packages/k53certbot/ -rf
ln -s /mnt/k53certbot /usr/local/lib/python3.8/site-packages/k53certbot -s
```
